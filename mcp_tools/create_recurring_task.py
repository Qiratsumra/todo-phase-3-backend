
"""
MCP Tool: create_recurring_task - Create a new recurring task.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from models import Task
from datetime import datetime, date, timezone
from enums import RecurrenceEnum
from utils.recurrence_parser import parse_recurrence_pattern, RecurrenceParseResult
import logging

logger = logging.getLogger("mcp_tools.create_recurring_task")

# Tool definition for Gemini function calling
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "create_recurring_task",
        "description": "Create a new recurring task with automatic next occurrence creation",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The title of the recurring task (required)"
                },
                "description": {
                    "type": "string",
                    "description": "Optional description of the task"
                },
                "priority": {
                    "type": "integer",
                    "description": "Priority level: 0=none, 1=low, 2=medium, 3=high",
                    "enum": [0, 1, 2, 3]
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date in YYYY-MM-DD format"
                },
                "recurrence": {
                    "type": "string",
                    "description": "Recurrence pattern: daily, weekly, monthly, or specific day (e.g., 'weekly:monday', 'monthly:15')"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tags for the task"
                }
            },
            "required": ["title", "recurrence"]
        }
    }
}


def execute(
    db: Session,
    title: str,
    recurrence: str,
    description: Optional[str] = None,
    priority: int = 0,
    due_date: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> dict:
    """
    Create a new recurring task.

    Args:
        db: Database session
        title: Task title
        recurrence: Recurrence pattern (daily, weekly, monthly, etc.)
        description: Task description
        priority: Priority level (0-3)
        due_date: Due date string (YYYY-MM-DD)
        tags: List of tags

    Returns:
        Dict with created task data including recurrence info
    """
    try:
        # Parse due_date if provided
        parsed_due_date = None
        if due_date:
            try:
                parsed_due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"Invalid due_date format: {due_date}")

        # Parse recurrence pattern
        parse_result = parse_recurrence_pattern(recurrence)
        if not parse_result.valid:
            return {
                "success": False,
                "error": parse_result.error_message or f"Invalid recurrence pattern: {recurrence}"
            }

        # Map to RecurrenceEnum
        recurrence_map = {
            "daily": RecurrenceEnum.DAILY,
            "weekly": RecurrenceEnum.WEEKLY,
            "monthly": RecurrenceEnum.MONTHLY,
        }
        recurrence_enum = recurrence_map.get(parse_result.frequency.value, RecurrenceEnum.NONE)

        # Generate pattern string for storage
        pattern_string = parse_result.to_pattern_string()

        task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=parsed_due_date,
            tags=tags or [],
            completed=False,
            recurrence=recurrence_enum,
            recurrence_pattern=pattern_string,
            created_at=datetime.now(timezone.utc)
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        logger.info(f"Created recurring task: {task.id} - {task.title} ({pattern_string})")

        return {
            "success": True,
            "task": {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "completed": task.completed,
                "priority": task.priority,
                "due_date": str(task.due_date) if task.due_date else None,
                "tags": task.tags,
                "recurrence": task.recurrence.value if task.recurrence else None,
                "recurrence_pattern": task.recurrence_pattern,
                "created_at": task.created_at.isoformat() if task.created_at else None
            },
            "recurrence_info": {
                "frequency": parse_result.frequency.value,
                "day_of_week": parse_result.day_of_week.value if parse_result.day_of_week else None,
                "day_of_month": parse_result.day_of_month,
                "next_occurrence_will_be_created_on_completion": True
            }
        }

    except Exception as e:
        logger.error(f"Error creating recurring task: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
