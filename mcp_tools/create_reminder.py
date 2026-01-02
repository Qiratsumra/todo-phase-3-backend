"""
MCP Tool: create_reminder - Schedule a reminder for a task.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import Task, Reminder, ReminderStatusEnum
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger("mcp_tools.create_reminder")

# Tool definition for Gemini function calling
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "create_reminder",
        "description": "Schedule a reminder for a task. The reminder will notify the user at the specified time.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "ID of the task to set a reminder for"
                },
                "offset_minutes": {
                    "type": "integer",
                    "description": "Minutes before due date to trigger reminder (5-10080 minutes)"
                },
                "offset_string": {
                    "type": "string",
                    "description": "Natural language offset like '30 minutes before', '1 hour', '1 day' (alternative to offset_minutes)"
                },
                "scheduled_at": {
                    "type": "string",
                    "description": "Exact date-time in ISO format (YYYY-MM-DDTHH:MM:SS) (alternative to offset)"
                }
            },
            "required": ["task_id"]
        }
    }
}


def execute(
    db: Session,
    task_id: int,
    offset_minutes: Optional[int] = None,
    offset_string: Optional[str] = None,
    scheduled_at: Optional[str] = None,
) -> dict:
    """
    Schedule a reminder for a task.

    Args:
        db: Database session
        task_id: ID of the task to set reminder for
        offset_minutes: Minutes before due date
        offset_string: Natural language offset
        scheduled_at: Exact scheduled time (ISO format)

    Returns:
        Dict with reminder data
    """
    try:
        # Verify task exists
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {
                "success": False,
                "error": f"Task with ID {task_id} not found"
            }

        # Verify task has due date
        if not task.due_date and not scheduled_at:
            return {
                "success": False,
                "error": "Task must have a due date or you must provide a scheduled time"
            }

        # Parse offset string if provided
        if offset_string:
            from utils.reminder_parser import parse_reminder_offset
            parse_result = parse_reminder_offset(offset_string)
            if not parse_result.valid:
                return {
                    "success": False,
                    "error": parse_result.error_message or f"Invalid offset: {offset_string}"
                }
            offset_minutes = parse_result.offset_minutes
            display_offset = parse_result.display_string
        else:
            display_offset = None

        # Calculate scheduled time
        if scheduled_at:
            try:
                scheduled_datetime = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
                if scheduled_datetime.tzinfo is None:
                    scheduled_datetime = scheduled_datetime.replace(tzinfo=timezone.utc)
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid datetime format: {scheduled_at}. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
                }
        elif offset_minutes:
            due_date = task.due_date
            if isinstance(due_date, date) and not isinstance(due_date, datetime):
                due_date = datetime.combine(due_date, datetime.min.time())
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
            scheduled_datetime = due_date - timedelta(minutes=offset_minutes)
            display_offset = f"{offset_minutes} minutes before due"
        else:
            return {
                "success": False,
                "error": "Must provide offset_minutes, offset_string, or scheduled_at"
            }

        # Validate scheduled time is in future
        if scheduled_datetime <= datetime.now(timezone.utc):
            return {
                "success": False,
                "error": "Reminder time must be in the future"
            }

        # Create reminder
        reminder = Reminder(
            task_id=task_id,
            user_id=1,  # Single-user demo
            scheduled_at=scheduled_datetime,
            status=ReminderStatusEnum.PENDING,
            offset_minutes=offset_minutes,
            offset_string=display_offset,
            created_at=datetime.now(timezone.utc),
        )

        db.add(reminder)
        db.commit()
        db.refresh(reminder)

        logger.info(f"Created reminder {reminder.id} for task {task_id}")

        return {
            "success": True,
            "reminder": {
                "id": reminder.id,
                "task_id": reminder.task_id,
                "scheduled_at": reminder.scheduled_at.isoformat() if reminder.scheduled_at else None,
                "status": reminder.status.value if reminder.status else None,
                "offset_minutes": reminder.offset_minutes,
                "offset_string": reminder.offset_string,
                "created_at": reminder.created_at.isoformat() if reminder.created_at else None,
            },
            "task": {
                "id": task.id,
                "title": task.title,
                "due_date": str(task.due_date) if task.due_date else None,
            }
        }

    except Exception as e:
        logger.error(f"Error creating reminder: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
