"""Phase V Enums for Task Management System.

This module defines all enums used throughout the Phase V implementation
for priorities, recurrence patterns, task status, and reminder status.
"""

from enum import Enum


class RecurrenceEnum(str, Enum):
    """Recurrence pattern for recurring tasks.

    Attributes:
        NONE: Task does not repeat.
        DAILY: Task repeats every day.
        WEEKLY: Task repeats every week.
        MONTHLY: Task repeats every month.
    """
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class PriorityEnum(str, Enum):
    """Priority levels for tasks.

    Attributes:
        LOW: Optional tasks, nice-to-have.
        MEDIUM: Normal tasks (default).
        HIGH: Urgent, important tasks.
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatusEnum(str, Enum):
    """Status of a task.

    Attributes:
        PENDING: Task is not yet completed.
        COMPLETED: Task has been marked as done.
    """
    PENDING = "pending"
    COMPLETED = "completed"


class ReminderStatusEnum(str, Enum):
    """Status of a reminder.

    Attributes:
        PENDING: Reminder is scheduled, not yet sent.
        SENT: Notification delivered successfully.
        FAILED: All retry attempts exhausted.
        CANCELLED: User cancelled the reminder.
    """
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Priority weight mapping for sorting/filtering operations
PRIORITY_WEIGHTS = {
    PriorityEnum.LOW: 1,
    PriorityEnum.MEDIUM: 2,
    PriorityEnum.HIGH: 3,
}


def get_priority_weight(priority: PriorityEnum) -> int:
    """Get numeric weight for priority enum value.

    Args:
        priority: The PriorityEnum value.

    Returns:
        Numeric weight (1 for low, 2 for medium, 3 for high).
    """
    return PRIORITY_WEIGHTS.get(priority, 2)  # Default to medium weight
