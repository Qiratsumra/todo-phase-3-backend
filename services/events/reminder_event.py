"""Reminder Event Schemas for Kafka/Dapr Pub/Sub.

This module provides Pydantic schemas for reminder-related events
published to the reminders Kafka topic.

Topics:
- reminders: Reminder scheduling and delivery events

Event Types:
- reminder.scheduled: Reminder was created/scheduled
- reminder.triggered: Dapr Jobs API fired the reminder
- reminder.sent: Notification was delivered to user
- reminder.failed: Notification delivery failed
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field


class ReminderEventType(str, Enum):
    """Reminder event types for reminders topic."""
    SCHEDULED = "reminder.scheduled"
    TRIGGERED = "reminder.triggered"
    SENT = "reminder.sent"
    FAILED = "reminder.failed"
    CANCELLED = "reminder.cancelled"


class ReminderScheduledEvent(BaseModel):
    """Event payload for reminder.scheduled events."""
    reminder_id: int
    task_id: int
    user_id: int = 1
    task_title: str
    scheduled_at: datetime
    reminder_offset: Optional[str] = None  # e.g., "1h", "30m"
    dapr_job_id: Optional[str] = None
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReminderTriggeredEvent(BaseModel):
    """Event payload for reminder.triggered events.

    This event is published when the Dapr Jobs API triggers
    the reminder callback, indicating it's time to notify the user.
    """
    reminder_id: int
    task_id: int
    user_id: int = 1
    task_title: str
    scheduled_at: datetime
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    dapr_job_id: Optional[str] = None
    correlation_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReminderSentEvent(BaseModel):
    """Event payload for reminder.sent events.

    This event is published after the notification was successfully
    delivered to the user (via push notification, email, etc.).
    """
    reminder_id: int
    task_id: int
    user_id: int = 1
    task_title: str
    scheduled_at: datetime
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    delivery_channel: str = "push"  # push, email, sms
    retry_count: int = 0
    correlation_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReminderFailedEvent(BaseModel):
    """Event payload for reminder.failed events.

    This event is published when notification delivery fails
    after all retry attempts are exhausted.
    """
    reminder_id: int
    task_id: int
    user_id: int = 1
    task_title: str
    scheduled_at: datetime
    failed_at: datetime = Field(default_factory=datetime.utcnow)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    correlation_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReminderCancelledEvent(BaseModel):
    """Event payload for reminder.cancelled events.

    This event is published when a scheduled reminder is cancelled
    before it triggers (e.g., task deleted or reminder removed).
    """
    reminder_id: int
    task_id: int
    user_id: int = 1
    task_title: Optional[str] = None
    scheduled_at: datetime
    cancelled_at: datetime = Field(default_factory=datetime.utcnow)
    reason: Optional[str] = None
    dapr_job_id: Optional[str] = None
    correlation_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReminderEvent(BaseModel):
    """Generic reminder event envelope for publishing to Kafka."""
    event_type: str
    reminder_id: int
    task_id: int
    user_id: int = 1
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    correlation_id: Optional[str] = None
    data: Dict[str, Any]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ========================================================================
# Event Factory Functions
# ========================================================================

def create_reminder_scheduled_event(
    reminder_id: int,
    task_id: int,
    task_title: str,
    scheduled_at: datetime,
    user_id: int = 1,
    reminder_offset: Optional[str] = None,
    dapr_job_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> ReminderScheduledEvent:
    """Factory function to create a reminder.scheduled event."""
    return ReminderScheduledEvent(
        reminder_id=reminder_id,
        task_id=task_id,
        user_id=user_id,
        task_title=task_title,
        scheduled_at=scheduled_at,
        reminder_offset=reminder_offset,
        dapr_job_id=dapr_job_id,
        status="pending",
        correlation_id=correlation_id,
    )


def create_reminder_triggered_event(
    reminder_id: int,
    task_id: int,
    task_title: str,
    scheduled_at: datetime,
    user_id: int = 1,
    dapr_job_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> ReminderTriggeredEvent:
    """Factory function to create a reminder.triggered event."""
    return ReminderTriggeredEvent(
        reminder_id=reminder_id,
        task_id=task_id,
        user_id=user_id,
        task_title=task_title,
        scheduled_at=scheduled_at,
        dapr_job_id=dapr_job_id,
        correlation_id=correlation_id,
    )


def create_reminder_sent_event(
    reminder_id: int,
    task_id: int,
    task_title: str,
    scheduled_at: datetime,
    user_id: int = 1,
    delivery_channel: str = "push",
    retry_count: int = 0,
    correlation_id: Optional[str] = None,
) -> ReminderSentEvent:
    """Factory function to create a reminder.sent event."""
    return ReminderSentEvent(
        reminder_id=reminder_id,
        task_id=task_id,
        user_id=user_id,
        task_title=task_title,
        scheduled_at=scheduled_at,
        delivery_channel=delivery_channel,
        retry_count=retry_count,
        correlation_id=correlation_id,
    )


def create_reminder_failed_event(
    reminder_id: int,
    task_id: int,
    task_title: str,
    scheduled_at: datetime,
    user_id: int = 1,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    retry_count: int = 0,
    max_retries: int = 3,
    correlation_id: Optional[str] = None,
) -> ReminderFailedEvent:
    """Factory function to create a reminder.failed event."""
    return ReminderFailedEvent(
        reminder_id=reminder_id,
        task_id=task_id,
        user_id=user_id,
        task_title=task_title,
        scheduled_at=scheduled_at,
        error_code=error_code,
        error_message=error_message,
        retry_count=retry_count,
        max_retries=max_retries,
        correlation_id=correlation_id,
    )


def create_reminder_cancelled_event(
    reminder_id: int,
    task_id: int,
    scheduled_at: datetime,
    user_id: int = 1,
    task_title: Optional[str] = None,
    reason: Optional[str] = None,
    dapr_job_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> ReminderCancelledEvent:
    """Factory function to create a reminder.cancelled event."""
    return ReminderCancelledEvent(
        reminder_id=reminder_id,
        task_id=task_id,
        user_id=user_id,
        task_title=task_title,
        scheduled_at=scheduled_at,
        reason=reason,
        dapr_job_id=dapr_job_id,
        correlation_id=correlation_id,
    )


# ========================================================================
# Event Parsing Utilities
# ========================================================================

def parse_reminder_event(event_data: Dict[str, Any]) -> ReminderEvent:
    """Parse incoming reminder event data into appropriate event type.

    Args:
        event_data: Raw event data from Kafka

    Returns:
        Specific reminder event instance based on event_type
    """
    event_type = event_data.get("event_type")

    event_map = {
        ReminderEventType.SCHEDULED: ReminderScheduledEvent,
        ReminderEventType.TRIGGERED: ReminderTriggeredEvent,
        ReminderEventType.SENT: ReminderSentEvent,
        ReminderEventType.FAILED: ReminderFailedEvent,
        ReminderEventType.CANCELLED: ReminderCancelledEvent,
    }

    event_class = event_map.get(event_type)
    if event_class:
        return ReminderEvent(
            event_type=event_type,
            reminder_id=event_data.get("reminder_id"),
            task_id=event_data.get("task_id"),
            user_id=event_data.get("user_id", 1),
            timestamp=event_data.get("timestamp"),
            correlation_id=event_data.get("correlation_id"),
            data=event_data,
        )

    raise ValueError(f"Unknown reminder event type: {event_type}")
