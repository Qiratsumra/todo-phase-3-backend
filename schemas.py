"""Pydantic schemas for API request/response validation.

This module defines all Pydantic models for Phase V including
task schemas with priorities, tags, recurrence patterns and reminder schemas.
"""

from pydantic import BaseModel, Field, validator, field_validator
from typing import List, Optional
from datetime import datetime, date, timedelta
from enum import Enum

from enums import RecurrenceEnum, PriorityEnum, TaskStatusEnum, ReminderStatusEnum


# ============================================================================
# Task Schemas
# ============================================================================

class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskRecurrence(str, Enum):
    """Task recurrence patterns."""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class TaskStatus(str, Enum):
    """Task completion status."""
    PENDING = "pending"
    COMPLETED = "completed"


class TaskBase(BaseModel):
    """Base schema for task data."""
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, max_length=10000, description="Task description")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    due_date: Optional[datetime] = Field(None, description="Due date and time")
    recurrence: TaskRecurrence = Field(default=TaskRecurrence.NONE, description="Recurrence pattern")

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate tags according to Phase V requirements."""
        if len(v) > 10:
            raise ValueError('Maximum 10 tags per task')
        validated_tags = []
        for tag in v:
            if not isinstance(tag, str):
                continue
            tag = tag.strip()
            if not tag:
                continue
            if not tag.startswith('#'):
                tag = f'#{tag}'
            if len(tag) > 50:
                raise ValueError(f'Tag too long (max 50 characters): {tag}')
            if tag not in validated_tags:
                validated_tags.append(tag)
        return validated_tags


class TaskCreate(TaskBase):
    """Schema for creating a new task."""
    project_id: Optional[int] = None
    pass


class TaskUpdate(BaseModel):
    """Schema for updating a task (partial update)."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=10000)
    priority: Optional[TaskPriority] = None
    tags: Optional[List[str]] = None
    due_date: Optional[datetime] = None
    recurrence: Optional[TaskRecurrence] = None
    completed: Optional[bool] = None

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate tags according to Phase V requirements."""
        if v is None:
            return None
        if len(v) > 10:
            raise ValueError('Maximum 10 tags per task')
        validated_tags = []
        for tag in v:
            if not isinstance(tag, str):
                continue
            tag = tag.strip()
            if not tag:
                continue
            if not tag.startswith('#'):
                tag = f'#{tag}'
            if len(tag) > 50:
                raise ValueError(f'Tag too long (max 50 characters): {tag}')
            if tag not in validated_tags:
                validated_tags.append(tag)
        return validated_tags


class Task(TaskBase):
    """Complete task schema with all fields."""
    id: int
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    parent_task_id: Optional[int] = None
    subtasks: List['Task'] = []

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    """API response schema for a single task."""
    id: int
    title: str
    description: Optional[str]
    status: str
    priority: str
    tags: List[str]
    due_date: Optional[datetime]
    recurrence: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    parent_task_id: Optional[int]
    subtasks: List['TaskResponse'] = []
    project: Optional['ProjectResponse'] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj) -> "TaskResponse":
        """Convert SQLAlchemy model to response schema."""
        # Safely access relationships to avoid DetachedInstanceError
        def safe_get(attr, default):
            try:
                return getattr(obj, attr, default)
            except Exception:
                return default

        children = safe_get('children', [])
        comments = safe_get('comments', [])
        attachments = safe_get('attachments', [])
        project = safe_get('project', None)

        return cls(
            id=obj.id,
            title=obj.title,
            description=obj.description,
            status=obj.status.value if hasattr(obj.status, 'value') else str(obj.status),
            priority=obj.priority.value if hasattr(obj.priority, 'value') else str(obj.priority),
            tags=obj.tags or [],
            due_date=obj.due_date,
            recurrence=obj.recurrence.value if hasattr(obj.recurrence, 'value') else str(obj.recurrence),
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            completed_at=obj.completed_at,
            parent_task_id=obj.parent_task_id,
            subtasks=[TaskResponse.from_orm(child) for child in children],
            comments=[CommentResponse.from_orm(comment) for comment in comments],
            attachments=[AttachmentResponse.from_orm(attachment) for attachment in attachments],
            project=ProjectResponse.from_orm(project) if project else None,
        )


class SubtaskCreate(BaseModel):
    """Schema for creating a subtask."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=10000)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    due_date: Optional[datetime] = None


class SubtaskResponse(TaskResponse):
    """Response schema for a subtask."""
    pass


class CommentCreate(BaseModel):
    """Schema for creating a comment."""
    content: str = Field(..., min_length=1, max_length=10000)


class CommentResponse(BaseModel):
    """Response schema for a comment."""
    id: int
    content: str
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj) -> "CommentResponse":
        """Convert SQLAlchemy model to response schema."""
        return cls(
            id=obj.id,
            content=obj.content,
            user_id=obj.user_id,
            created_at=obj.created_at,
        )


class AttachmentCreate(BaseModel):
    """Schema for creating an attachment."""
    file_name: str
    file_url: str


class AttachmentResponse(BaseModel):
    """Response schema for an attachment."""
    id: int
    file_name: str
    file_url: str
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj) -> "AttachmentResponse":
        """Convert SQLAlchemy model to response schema."""
        return cls(
            id=obj.id,
            file_name=obj.file_name,
            file_url=obj.file_url,
            created_at=obj.created_at,
        )


class TaskListResponse(BaseModel):
    """API response schema for a list of tasks."""
    tasks: List[TaskResponse]
    total_count: int
    page: int
    page_size: int


# ============================================================================
# Project Schemas
# ============================================================================

class ProjectCreate(BaseModel):
    """Schema for creating a project."""
    name: str = Field(..., min_length=1, max_length=255)


class ProjectResponse(BaseModel):
    """Response schema for a project."""
    id: int
    name: str

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj) -> "ProjectResponse":
        """Convert SQLAlchemy model to response schema."""
        return cls(
            id=obj.id,
            name=obj.name,
        )

# ============================================================================
# Priority Update Schemas
# ============================================================================

class UpdatePriorityRequest(BaseModel):
    """Request schema for updating task priority."""
    priority: TaskPriority = Field(..., description="New priority level (low, medium, high)")


class UpdatePriorityResponse(TaskResponse):
    """Response schema for priority update."""
    pass


# ============================================================================
# Tag Management Schemas
# ============================================================================

class AddTagsRequest(BaseModel):
    """Request schema for adding tags to a task."""
    tags: List[str] = Field(..., min_length=1, description="Tags to add (will be prefixed with # if needed)")

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate and format tags."""
        if len(v) > 10:
            raise ValueError('Maximum 10 tags per task')
        validated_tags = []
        for tag in v:
            tag = tag.strip()
            if not tag:
                continue
            if not tag.startswith('#'):
                tag = f'#{tag}'
            if len(tag) > 50:
                raise ValueError(f'Tag too long (max 50 characters): {tag}')
            if tag not in validated_tags:
                validated_tags.append(tag)
        return validated_tags


class RemoveTagsRequest(BaseModel):
    """Request schema for removing tags from a task."""
    tags: List[str] = Field(..., min_length=1, description="Tags to remove")


class TagsResponse(TaskResponse):
    """Response schema for tag operations."""
    pass


# ============================================================================
# Reminder Schemas
# ============================================================================

class ReminderStatus(str, Enum):
    """Reminder status values."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReminderBase(BaseModel):
    """Base schema for reminder data."""
    task_id: int = Field(..., description="Associated task ID")
    scheduled_at: datetime = Field(..., description="When reminder should fire")


class ReminderCreate(ReminderBase):
    """Schema for creating a new reminder."""
    reminder_type: str = Field(default="websocket", description="Notification type")


class ReminderUpdate(BaseModel):
    """Schema for updating a reminder."""
    scheduled_at: Optional[datetime] = None
    status: Optional[ReminderStatus] = None


class ReminderResponse(BaseModel):
    """API response schema for a reminder."""
    id: int
    task_id: int
    user_id: int
    scheduled_at: datetime
    reminder_type: str
    status: str
    retry_count: int
    dapr_job_id: Optional[str]
    created_at: datetime
    sent_at: Optional[datetime]

    class Config:
        from_attributes = True


class ReminderListResponse(BaseModel):
    """API response schema for a list of reminders."""
    reminders: List[ReminderResponse]
    total_count: int


# Valid reminder offsets for user-friendly input
VALID_REMINDER_OFFSETS = [
    "15 minutes",
    "30 minutes",
    "1 hour",
    "2 hours",
    "4 hours",
    "1 day",
    "2 days",
    "1 week",
]


def parse_reminder_offset(offset_str: str) -> timedelta:
    """Parse reminder offset string to timedelta.

    Args:
        offset_str: Offset string like "1 day", "2 hours", "30 minutes"

    Returns:
        timedelta representing the offset

    Raises:
        ValueError: If offset format is invalid
    """
    import re

    patterns = [
        (r'^(\d+)\s*minute[s]?$', lambda m: timedelta(minutes=int(m.group(1)))),
        (r'^(\d+)\s*hour[s]?$', lambda m: timedelta(hours=int(m.group(1)))),
        (r'^(\d+)\s*day[s]?$', lambda m: timedelta(days=int(m.group(1)))),
        (r'^(\d+)\s*week[s]?$', lambda m: timedelta(weeks=int(m.group(1)))),
    ]

    for pattern, converter in patterns:
        match = re.match(pattern, offset_str.lower().strip())
        if match:
            return converter(match)

    raise ValueError(
        f"Invalid reminder offset format. Must be one of: {VALID_REMINDER_OFFSETS}"
    )


# ============================================================================
# Recurrence Schemas
# ============================================================================

class RecurrenceInfo(BaseModel):
    """Information about task recurrence."""
    pattern: str = Field(..., description="Recurrence pattern (none, daily, weekly, monthly)")
    next_occurrence: Optional[datetime] = Field(None, description="Next occurrence due date")
    parent_task_id: Optional[int] = Field(None, description="Parent task ID if this is a recurrence")


# ============================================================================
# Search/Filter Schemas
# ============================================================================

class TaskFilter(BaseModel):
    """Filter criteria for task queries."""
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    tags: Optional[List[str]] = None
    due_before: Optional[datetime] = None
    due_after: Optional[datetime] = None
    is_recurring: Optional[bool] = None


class TaskSort(str, Enum):
    """Sort options for task queries."""
    CREATED_AT = "created_at"
    DUE_DATE = "due_date"
    PRIORITY = "priority"
    TITLE = "title"


class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


class TaskSearchRequest(BaseModel):
    """Request schema for advanced task search."""
    query: Optional[str] = Field(None, description="Natural language search query")
    filters: Optional[TaskFilter] = None
    sort_by: TaskSort = Field(default=TaskSort.CREATED_AT)
    order: SortOrder = Field(default=SortOrder.DESC)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class TaskSearchResponse(BaseModel):
    """Response schema for task search results."""
    results: List[TaskResponse]
    total_count: int
    query: Optional[str] = None


# ============================================================================
# Event Schemas (for Kafka/Dapr)
# ============================================================================

class TaskEventType(str, Enum):
    """Task event types for event-driven architecture."""
    CREATED = "task.created"
    UPDATED = "task.updated"
    COMPLETED = "task.completed"
    DELETED = "task.deleted"


class TaskEvent(BaseModel):
    """Event schema for task lifecycle events."""
    event_type: TaskEventType
    task_id: int
    task_data: dict
    user_id: int = 1  # Single-user demo
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None


class ReminderEventType(str, Enum):
    """Reminder event types."""
    SCHEDULED = "reminder.scheduled"
    TRIGGERED = "reminder.triggered"
    SENT = "reminder.sent"
    FAILED = "reminder.failed"


class ReminderEvent(BaseModel):
    """Event schema for reminder events."""
    event_type: ReminderEventType
    reminder_id: int
    task_id: int
    user_id: int = 1
    scheduled_at: datetime
    status: str
    retry_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None


# ============================================================================
# Health Check Schemas
# ============================================================================

class HealthStatus(str, Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class ServiceHealth(BaseModel):
    """Health status of an individual service."""
    status: HealthStatus
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Overall health check response."""
    status: HealthStatus
    services: dict[str, ServiceHealth]
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
