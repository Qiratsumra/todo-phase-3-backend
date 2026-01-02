# ========================================================================
# Dapr Pub/Sub Consumer for Reminder Events
# ========================================================================

import asyncio
import json
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any

from dapr.clients import DaprClient

logger = logging.getLogger(__name__)


@dataclass
class ReminderEvent:
    event_type: str
    user_id: str
    task_id: int
    task_title: str
    reminder_type: str
    due_date: Optional[str]
    scheduled_at: str
    message: str
    metadata: Dict[str, Any] = None

    @classmethod
    def from_dict(cls, data: dict) -> "ReminderEvent":
        return cls(
            event_type=data.get("event_type", "reminder.triggered"),
            user_id=data.get("user_id", ""),
            task_id=data.get("task_id", 0),
            task_title=data.get("task_title", ""),
            reminder_type=data.get("reminder_type", "due_soon"),
            due_date=data.get("due_date"),
            scheduled_at=data.get("scheduled_at", datetime.utcnow().isoformat()),
            message=data.get("message", "Task reminder"),
            metadata=data.get("metadata", {})
        )


@dataclass
class NotificationStats:
    events_received: int = 0
    notifications_sent: int = 0
    errors_count: int = 0


class ReminderEventConsumer:
    PUBSUB_NAME = "kafka-pubsub"
    TOPIC_NAME = "reminders"

    def __init__(self, dapr_client: DaprClient, connection_manager):
        self.dapr_client = dapr_client
        self.connection_manager = connection_manager
        self.is_running = False
        self._stats = NotificationStats()
        self._lock = asyncio.Lock()

    async def start_consuming(self):
        logger.info(f"Starting to consume from {self.TOPIC_NAME}...")
        self.is_running = True
        while self.is_running:
            try:
                subscription = self.dapr_client.subscribe(
                    pubsub_name=self.PUBSUB_NAME,
                    topic=self.TOPIC_NAME,
                    handler=self._handle_event
                )
                while self.is_running:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        self.is_running = False

    async def _handle_event(self, event):
        try:
            data = json.loads(event.data.decode("utf-8"))
            await self.process_event(data)
            return True, "OK"
        except Exception as e:
            logger.error(f"Error: {e}")
            async with self._lock:
                self._stats.errors_count += 1
            return False, str(e)

    async def process_event(self, data: dict):
        event = ReminderEvent.from_dict(data)
        logger.info(f"Processing reminder for user {event.user_id}")

        notification = {
            "type": "reminder",
            "task_id": event.task_id,
            "task_title": event.task_title,
            "reminder_type": event.reminder_type,
            "message": event.message,
            "due_date": event.due_date
        }

        if self.connection_manager.is_user_connected(event.user_id):
            sent = await self.connection_manager.send_personal_message(notification, event.user_id)
            if sent > 0:
                async with self._lock:
                    self._stats.notifications_sent += sent
        else:
            logger.info(f"User {event.user_id} not connected. Notification stored.")

        async with self._lock:
            self._stats.events_received += 1

    def get_stats(self):
        return self._stats
