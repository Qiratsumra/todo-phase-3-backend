# ========================================================================
# Dapr Pub/Sub Consumer for Task Events
# ========================================================================

import asyncio
import json
import logging
from datetime import datetime
from dataclasses import dataclass

from dapr.clients import DaprClient

logger = logging.getLogger(__name__)


@dataclass
class TaskStats:
    events_processed: int = 0
    tasks_created: int = 0
    errors_count: int = 0
    last_event_time: Optional[datetime] = None


class TaskEventConsumer:
    PUBSUB_NAME = "kafka-pubsub"
    TOPIC_NAME = "task-events"

    def __init__(self, dapr_client: DaprClient, scheduler, api_client):
        self.dapr_client = dapr_client
        self.scheduler = scheduler
        self.api_client = api_client
        self.is_running = False
        self._stats = TaskStats()

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
            self._stats.errors_count += 1
            return False, str(e)

    async def process_event(self, data: dict):
        event_type = data.get("event_type", "")
        if event_type != "task.completed":
            return

        task_id = data.get("task_id", 0)
        recurrence = data.get("recurrence")
        if not recurrence:
            return

        logger.info(f"Processing completed task {task_id}")

        next_occ = self.scheduler.calculate_next_occurrence(recurrence)
        if not next_occ:
            return

        success = await self.api_client.create_next_occurrence(
            user_id=data.get("user_id"),
            title=data.get("title"),
            description=data.get("description"),
            priority=data.get("priority", "medium"),
            due_date=next_occ.isoformat(),
            recurrence=recurrence,
            parent_task_id=task_id
        )

        if success:
            self._stats.tasks_created += 1
        else:
            self._stats.errors_count += 1
        self._stats.events_processed += 1
        self._stats.last_event_time = datetime.utcnow()

    def get_stats(self):
        return self._stats
