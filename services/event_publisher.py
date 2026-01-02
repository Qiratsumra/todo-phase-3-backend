"""Dapr Pub/Sub Event Publisher for Kafka.

This module provides to EventPublisher class for publishing events
to Kafka topics via Dapr Pub/Sub building block.

Topics:
- task-events: Task lifecycle events (created, updated, completed, deleted)
- reminders: Reminder scheduling and delivery events
- task-updates: Real-time task update notifications
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import uuid4

import httpx
from pydantic import BaseModel

logger = logging.getLogger("app")


# ========================================================================
# Event Schemas
# ========================================================================

class TaskEventType(str):
    """Task event types for task-events topic."""
    CREATED = "task.created"
    UPDATED = "task.updated"
    COMPLETED = "task.completed"
    DELETED = "task.deleted"


class ReminderEventType(str):
    """Reminder event types for reminders topic."""
    SCHEDULED = "reminder.scheduled"
    TRIGGERED = "reminder.triggered"
    SENT = "reminder.sent"
    FAILED = "reminder.failed"


class TaskEvent(BaseModel):
    """Event schema for task lifecycle events."""
    event_type: str
    task_id: int
    task_data: Dict[str, Any]
    user_id: int = 1  # Single-user demo
    timestamp: str = datetime.now(timezone.utc).isoformat()
    correlation_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReminderEvent(BaseModel):
    """Event schema for reminder events."""
    event_type: str
    reminder_id: int
    task_id: int
    user_id: int = 1
    scheduled_at: str
    reminder_offset: Optional[str] = None
    dapr_job_id: Optional[str] = None
    status: str
    retry_count: int = 0
    timestamp: str = datetime.now(timezone.utc).isoformat()
    correlation_id: Optional[str] = None


class TaskUpdateEvent(BaseModel):
    """Event schema for real-time task updates."""
    event_type: str
    task_id: int
    update_data: Dict[str, Any]
    user_id: int = 1
    timestamp: str = datetime.now(timezone.utc).isoformat()
    correlation_id: Optional[str] = None


# ========================================================================
# Event Publisher
# ========================================================================

class EventPublisher:
    """Publisher for events to Kafka via Dapr Pub/Sub.

    This class provides methods to publish events to various Kafka topics
    using to Dapr Pub/Sub HTTP API.

    Dapr Pub/Sub HTTP API:
    POST http://localhost:3500/v1.0/publish/{pubsub-name}/{topic}

    Attributes:
        pubsub_name: Name of the Dapr Pub/Sub component (default: kafka-pubsub)
        base_url: Base URL for the Dapr sidecar (default: http://localhost:3500)
        http_client: Async HTTP client for API calls
    """

    def __init__(
        self,
        pubsub_name: str = "kafka-pubsub",
        base_url: str = "http://localhost:3500",
        timeout: float = 10.0,
    ):
        """Initialize the event publisher.

        Args:
            pubsub_name: Name of the Dapr Pub/Sub component
            base_url: Base URL for the Dapr sidecar
            timeout: Request timeout in seconds
        """
        self.pubsub_name = pubsub_name
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.http_client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for event tracing."""
        return str(uuid4())

    async def _publish(
        self,
        topic: str,
        data: Dict[str, Any],
        data_content_type: str = "application/json",
    ) -> bool:
        """Publish an event to a Dapr Pub/Sub topic.

        Args:
            topic: The Kafka topic to publish to
            data: Event data as a dictionary
            data_content_type: Content type for the data (default: application/json)

        Returns:
            True if the publish was successful, False otherwise

        Raises:
            Exception: If publish fails (logged but not raised)
        """
        url = f"{self.base_url}/v1.0/publish/{self.pubsub_name}/{topic}"

        headers = {
            "Content-Type": data_content_type,
            "X-Correlation-Id": data.get("correlation_id", self._generate_correlation_id()),
        }

        try:
            response = await self.http_client.post(
                url,
                content=json.dumps(data),
                headers=headers,
            )

            if response.status_code in (200, 204, 201):
                logger.info(f"Published event to topic '{topic}': {response.status_code}")
                return True
            else:
                logger.error(
                    f"Failed to publish to topic '{topic}': "
                    f"{response.status_code} - {response.text}"
                )
                return False

        except httpx.RequestError as e:
            logger.error(f"Request error publishing to topic '{topic}': {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error publishing to topic '{topic}': {e}")
            return False

    # ========================================================================
    # Task Events
    # ========================================================================

    async def publish_task_created(
        self,
        task_id: int,
        task_data: Dict[str, Any],
        user_id: int = 1,
    ) -> bool:
        """Publish a task.created event.

        Args:
            task_id: ID of the created task
            task_data: Task data dictionary
            user_id: User ID (default: 1 for single-user demo)

        Returns:
            True if successful
        """
        event = TaskEvent(
            event_type=TaskEventType.CREATED,
            task_id=task_id,
            task_data=task_data,
            user_id=user_id,
            correlation_id=self._generate_correlation_id(),
        )
        return await self._publish("task-events", event.model_dump())

    async def publish_task_updated(
        self,
        task_id: int,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        user_id: int = 1,
    ) -> bool:
        """Publish a task.updated event.

        Args:
            task_id: ID of the updated task
            old_data: Previous task data
            new_data: Updated task data
            user_id: User ID

        Returns:
            True if successful
        """
        event = TaskEvent(
            event_type=TaskEventType.UPDATED,
            task_id=task_id,
            task_data={"old": old_data, "new": new_data},
            user_id=user_id,
            correlation_id=self._generate_correlation_id(),
        )
        return await self._publish("task-events", event.model_dump())

    async def publish_task_completed(
        self,
        task_id: int,
        task_data: Dict[str, Any],
        is_recurring: bool = False,
        user_id: int = 1,
    ) -> bool:
        """Publish a task.completed event.

        Args:
            task_id: ID of the completed task
            task_data: Task data
            is_recurring: Whether this is a recurring task
            user_id: User ID

        Returns:
            True if successful
        """
        event_data = {
            **task_data,
            "is_recurring": is_recurring,
        }
        event = TaskEvent(
            event_type=TaskEventType.COMPLETED,
            task_id=task_id,
            task_data=event_data,
            user_id=user_id,
            correlation_id=self._generate_correlation_id(),
        )
        return await self._publish("task-events", event.model_dump())

    async def publish_task_deleted(
        self,
        task_id: int,
        task_data: Dict[str, Any],
        user_id: int = 1,
    ) -> bool:
        """Publish a task.deleted event.

        Args:
            task_id: ID of the deleted task
            task_data: Last known task data
            user_id: User ID

        Returns:
            True if successful
        """
        event = TaskEvent(
            event_type=TaskEventType.DELETED,
            task_id=task_id,
            task_data=task_data,
            user_id=user_id,
            correlation_id=self._generate_correlation_id(),
        )
        return await self._publish("task-events", event.model_dump())

    # ========================================================================
    # Reminder Events
    # ========================================================================

    async def publish_reminder_scheduled(
        self,
        reminder_id: int,
        task_id: int,
        scheduled_at: str,
        reminder_offset: Optional[str] = None,
        dapr_job_id: Optional[str] = None,
        user_id: int = 1,
    ) -> bool:
        """Publish a reminder.scheduled event.

        Args:
            reminder_id: ID of the created reminder
            task_id: Associated task ID
            scheduled_at: When the reminder should fire (ISO 8601)
            reminder_offset: Offset before the due date
            dapr_job_id: Dapr Jobs API job ID
            user_id: User ID

        Returns:
            True if successful
        """
        event = ReminderEvent(
            event_type=ReminderEventType.SCHEDULED,
            reminder_id=reminder_id,
            task_id=task_id,
            scheduled_at=scheduled_at,
            reminder_offset=reminder_offset,
            dapr_job_id=dapr_job_id,
            status="pending",
            user_id=user_id,
            correlation_id=self._generate_correlation_id(),
        )
        return await self._publish("reminders", event.model_dump())

    async def publish_reminder_triggered(
        self,
        reminder_id: int,
        task_id: int,
        scheduled_at: str,
        user_id: int = 1,
    ) -> bool:
        """Publish a reminder.triggered event (when Dapr Jobs API fires).

        Args:
            reminder_id: ID of the triggered reminder
            task_id: Associated task ID
            scheduled_at: Original scheduled time
            user_id: User ID

        Returns:
            True if successful
        """
        event = ReminderEvent(
            event_type=ReminderEventType.TRIGGERED,
            reminder_id=reminder_id,
            task_id=task_id,
            scheduled_at=scheduled_at,
            status="triggered",
            user_id=user_id,
            correlation_id=self._generate_correlation_id(),
        )
        return await self._publish("reminders", event.model_dump())

    async def publish_reminder_sent(
        self,
        reminder_id: int,
        task_id: int,
        scheduled_at: str,
        retry_count: int = 0,
        user_id: int = 1,
    ) -> bool:
        """Publish a reminder.sent event (notification delivered).

        Args:
            reminder_id: ID of the sent reminder
            task_id: Associated task ID
            scheduled_at: Original scheduled time
            retry_count: Number of retry attempts
            user_id: User ID

        Returns:
            True if successful
        """
        event = ReminderEvent(
            event_type=ReminderEventType.SENT,
            reminder_id=reminder_id,
            task_id=task_id,
            scheduled_at=scheduled_at,
            status="sent",
            retry_count=retry_count,
            user_id=user_id,
            correlation_id=self._generate_correlation_id(),
        )
        return await self._publish("reminders", event.model_dump())

    async def publish_reminder_failed(
        self,
        reminder_id: int,
        task_id: int,
        scheduled_at: str,
        retry_count: int,
        error: Optional[str] = None,
        user_id: int = 1,
    ) -> bool:
        """Publish a reminder.failed event (notification delivery failed).

        Args:
            reminder_id: ID of the failed reminder
            task_id: Associated task ID
            scheduled_at: Original scheduled time
            retry_count: Current retry count
            error: Error message
            user_id: User ID

        Returns:
            True if successful
        """
        event = ReminderEvent(
            event_type=ReminderEventType.FAILED,
            reminder_id=reminder_id,
            task_id=task_id,
            scheduled_at=scheduled_at,
            status="failed",
            retry_count=retry_count,
            user_id=user_id,
            correlation_id=self._generate_correlation_id(),
        )
        # Add error to event data
        event_data = event.model_dump()
        if error:
            event_data["error"] = error
        return await self._publish("reminders", event_data)

    # ========================================================================
    # Task Update Events (Real-time Notifications)
    # ========================================================================

    async def publish_task_update(
        self,
        event_type: str,
        task_id: int,
        update_data: Dict[str, Any],
        user_id: int = 1,
    ) -> bool:
        """Publish a task update event for real-time notifications.

        Args:
            event_type: Type of the update (task.created, task.updated, etc.)
            task_id: ID of the affected task
            update_data: Changed fields
            user_id: User ID

        Returns:
            True if successful
        """
        event = TaskUpdateEvent(
            event_type=event_type,
            task_id=task_id,
            update_data=update_data,
            user_id=user_id,
            correlation_id=self._generate_correlation_id(),
        )
        return await self._publish("task-updates", event.model_dump())


# ========================================================================
# Singleton Instance
# ========================================================================

_event_publisher: Optional[EventPublisher] = None


def get_event_publisher() -> EventPublisher:
    """Get or create the singleton event publisher instance.

    Returns:
        EventPublisher instance
    """
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = EventPublisher()
    return _event_publisher


async def close_event_publisher():
    """Close the singleton event publisher."""
    global _event_publisher
    if _event_publisher:
        await _event_publisher.close()
        _event_publisher = None
