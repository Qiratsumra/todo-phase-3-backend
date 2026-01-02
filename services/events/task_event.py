"""Task Event Schemas for Kafka/Dapr Pub/Sub.

This module provides Pydantic schemas for task-related events
published to the task-events Kafka topic.

Topics:
- task-events: Task lifecycle events (created, updated, completed, deleted)

Event Types:
- task.created: New task was created
- task.updated: Task was modified
- task.completed: Task was completed
- task.deleted: Task was deleted
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field


class TaskEventType(str, Enum):
    """Task event types for task-events topic."""
    CREATED = "task.created"
    UPDATED = "task.updated"
    COMPLETED = "task.completed"
    DELETED = "task.deleted"


class TaskCreatedEvent(BaseModel):
    """Event payload for task.created events."""
    task_id: int
    user_id: int = 1
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    status: str = "pending"
    due_date: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None
    parent_task_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskUpdatedEvent(BaseModel):
    """Event payload for task.updated events."""
    task_id: int
    user_id: int = 1
    old_data: Dict[str, Any]
    new_data: Dict[str, Any]
    changed_fields: List[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskCompletedEvent(BaseModel):
    """Event payload for task.completed events."""
    task_id: int
    user_id: int = 1
    title: str
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    is_recurring: bool = False
    parent_task_id: Optional[int] = None
    next_occurrence_id: Optional[int] = None
    correlation_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskDeletedEvent(BaseModel):
    """Event payload for task.deleted events."""
    task_id: int
    user_id: int = 1
    title: str
    deleted_at: datetime = Field(default_factory=datetime.utcnow)
    cascade_delete: bool = False
    deleted_task_ids: List[int] = Field(default_factory=list)
    correlation_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskEvent(BaseModel):
    """Generic task event envelope for publishing to Kafka."""
    event_type: str
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

def create_task_created_event(
    task_id: int,
    title: str,
    user_id: int = 1,
    description: Optional[str] = None,
    priority: str = "medium",
    due_date: Optional[datetime] = None,
    tags: Optional[List[str]] = None,
    is_recurring: bool = False,
    recurrence_pattern: Optional[str] = None,
    parent_task_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
) -> TaskCreatedEvent:
    """Factory function to create a task.created event."""
    return TaskCreatedEvent(
        task_id=task_id,
        user_id=user_id,
        title=title,
        description=description,
        priority=priority,
        status="pending",
        due_date=due_date,
        tags=tags or [],
        is_recurring=is_recurring,
        recurrence_pattern=recurrence_pattern,
        parent_task_id=parent_task_id,
        correlation_id=correlation_id,
    )


def create_task_updated_event(
    task_id: int,
    old_data: Dict[str, Any],
    new_data: Dict[str, Any],
    user_id: int = 1,
    changed_fields: Optional[List[str]] = None,
    correlation_id: Optional[str] = None,
) -> TaskUpdatedEvent:
    """Factory function to create a task.updated event."""
    return TaskUpdatedEvent(
        task_id=task_id,
        user_id=user_id,
        old_data=old_data,
        new_data=new_data,
        changed_fields=changed_fields or list(set(new_data.keys()) - set(old_data.keys())),
        correlation_id=correlation_id,
    )


def create_task_completed_event(
    task_id: int,
    title: str,
    user_id: int = 1,
    is_recurring: bool = False,
    parent_task_id: Optional[int] = None,
    next_occurrence_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
) -> TaskCompletedEvent:
    """Factory function to create a task.completed event."""
    return TaskCompletedEvent(
        task_id=task_id,
        user_id=user_id,
        title=title,
        is_recurring=is_recurring,
        parent_task_id=parent_task_id,
        next_occurrence_id=next_occurrence_id,
        correlation_id=correlation_id,
    )


def create_task_deleted_event(
    task_id: int,
    title: str,
    user_id: int = 1,
    cascade_delete: bool = False,
    deleted_task_ids: Optional[List[int]] = None,
    correlation_id: Optional[str] = None,
) -> TaskDeletedEvent:
    """Factory function to create a task.deleted event."""
    return TaskDeletedEvent(
        task_id=task_id,
        user_id=user_id,
        title=title,
        cascade_delete=cascade_delete,
        deleted_task_ids=deleted_task_ids or [],
        correlation_id=correlation_id,
    )
