"""SQLAlchemy models for the Task Management System.

This module defines all database models including Task, Reminder, AuditLogEntry,
Conversation, and Message entities for Phase V implementation.
"""

from sqlalchemy import (
    Boolean, Column, Integer, String, Text, DateTime, ARRAY,
    ForeignKey, Index, JSON, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, INTERVAL
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone
from enum import Enum

from enums import RecurrenceEnum, PriorityEnum, TaskStatusEnum, ReminderStatusEnum

Base = declarative_base()


class Conversation(Base):
    """Represents a chat session between a user and the AI assistant."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Project(Base):
    """Represents a project or list that contains tasks."""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)

    tasks = relationship("Task", back_populates="project")


class Message(Base):
    """Represents a single message in a conversation (user or assistant)."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)
    skill_used = Column(String(50), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    conversation = relationship("Conversation", back_populates="messages")


class Task(Base):
    """Task entity with Phase V enhanced fields for priorities, tags, and recurrence.

    Attributes:
        id: Unique identifier for the task.
        title: Task title (required).
        description: Optional detailed description.
        due_date: When the task is due.
        recurrence: Recurrence pattern (none, daily, weekly, monthly).
        priority: Task priority (low, medium, high).
        tags: Array of tags for categorization.
        status: Task status (pending, completed).
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        completed_at: When the task was completed.
        parent_task_id: Reference to parent task for recurring task chains.
        reminder_offset: Time offset before due date for reminders.
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, default="")
    due_date = Column(TIMESTAMP(timezone=True), nullable=True)
    recurrence = Column(
        SQLEnum(RecurrenceEnum),
        default=RecurrenceEnum.NONE,
        nullable=False
    )
    priority = Column(
        SQLEnum(PriorityEnum),
        default=PriorityEnum.MEDIUM,
        nullable=False
    )
    tags = Column(ARRAY(String), default=[])
    status = Column(
        SQLEnum(TaskStatusEnum),
        default=TaskStatusEnum.PENDING,
        nullable=False
    )
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    parent_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    reminder_offset = Column(INTERVAL, nullable=True)

    # Relationships
    parent = relationship("Task", remote_side=[id], back_populates="children")
    children = relationship("Task", back_populates="parent", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="task", cascade="all, delete-orphan")
    audit_entries = relationship("AuditLogEntry", back_populates="task", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="task", cascade="all, delete-orphan")
    project = relationship("Project", back_populates="tasks")
    
    # Indexes for Phase V performance requirements
    __table_args__ = (
        Index("idx_tasks_priority_due_date", "priority", "due_date"),
        Index("idx_tasks_tags_gin", "tags", postgresql_using="gin"),
        Index("idx_tasks_parent_id", "parent_task_id"),
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_created_at", "created_at"),
        Index("idx_tasks_recurrence", "recurrence"),
    )

    def to_dict(self) -> dict:
        """Convert task to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "recurrence": self.recurrence.value if self.recurrence else None,
            "priority": self.priority.value if self.priority else None,
            "tags": self.tags or [],
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "parent_task_id": self.parent_task_id,
            "reminder_offset": str(self.reminder_offset) if self.reminder_offset else None,
            "subtasks": [child.to_dict() for child in self.children],
        }

    def is_recurring(self) -> bool:
        """Check if task has a recurrence pattern."""
        return self.recurrence is not None and self.recurrence != RecurrenceEnum.NONE


class Comment(Base):
    """Represents a comment on a task."""
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    task = relationship("Task", back_populates="comments")


class Attachment(Base):
    """Represents an attachment for a task."""
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(2048), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    task = relationship("Task", back_populates="attachments")


class Reminder(Base):
    """Reminder entity for task notifications.

    Attributes:
        id: Unique identifier for the reminder.
        task_id: Reference to the associated task.
        user_id: User ID (single-user demo: always 1).
        scheduled_at: When the reminder should fire.
        reminder_type: Type of notification (websocket, email, push).
        status: Reminder status (pending, sent, failed, cancelled).
        retry_count: Number of retry attempts.
        dapr_job_id: Dapr Jobs API job ID for scheduling.
        created_at: Creation timestamp.
        sent_at: When the reminder was sent.
    """
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, default=1, nullable=False)  # Single-user demo
    scheduled_at = Column(TIMESTAMP(timezone=True), nullable=False)
    reminder_type = Column(String(50), default="websocket")
    status = Column(
        SQLEnum(ReminderStatusEnum),
        default=ReminderStatusEnum.PENDING,
        nullable=False
    )
    retry_count = Column(Integer, default=0)
    dapr_job_id = Column(String(255), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    task = relationship("Task", back_populates="reminders")

    # Indexes
    __table_args__ = (
        Index("idx_reminders_task_id", "task_id"),
        Index("idx_reminders_status", "status"),
        Index("idx_reminders_scheduled_at", "scheduled_at"),
        Index("idx_reminders_dapr_job_id", "dapr_job_id"),
    )

    def to_dict(self) -> dict:
        """Convert reminder to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "reminder_type": self.reminder_type,
            "status": self.status.value if self.status else None,
            "retry_count": self.retry_count,
            "dapr_job_id": self.dapr_job_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }

    def is_pending(self) -> bool:
        """Check if reminder is still pending."""
        return self.status == ReminderStatusEnum.PENDING

    def can_retry(self) -> bool:
        """Check if reminder can be retried (less than 3 attempts)."""
        return self.retry_count < 3 and self.status == ReminderStatusEnum.FAILED


class AuditLogEntry(Base):
    """Audit log entry for tracking task operations and events.

    Attributes:
        id: Unique identifier for the audit entry.
        event_id: Unique event identifier (UUID).
        event_type: Type of event (created, updated, completed, deleted, reminder_triggered).
        task_id: Reference to the task.
        parent_task_id: Reference to parent task for recurring chains.
        user_id: User ID (single-user demo: always 1).
        event_data: Full event payload as JSON.
        created_at: When the event occurred.
    """
    __tablename__ = "audit_log_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(255), unique=True, nullable=False)
    event_type = Column(String(100), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    parent_task_id = Column(Integer, nullable=True)
    user_id = Column(Integer, default=1, nullable=False)
    event_data = Column(JSON, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    task = relationship("Task", back_populates="audit_entries")

    # Indexes
    __table_args__ = (
        Index("idx_audit_event_id", "event_id"),
        Index("idx_audit_event_type", "event_type"),
        Index("idx_audit_task_id", "task_id"),
        Index("idx_audit_parent_task_id", "parent_task_id"),
        Index("idx_audit_created_at", "created_at"),
    )

    def to_dict(self) -> dict:
        """Convert audit entry to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "task_id": self.task_id,
            "parent_task_id": self.parent_task_id,
            "user_id": self.user_id,
            "event_data": self.event_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }