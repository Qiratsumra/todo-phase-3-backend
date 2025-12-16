"""
MCP Tool: add_task - Create a new task.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from models import Task
from datetime import datetime, date, timezone
import logging

logger = logging.getLogger("mcp_tools.add_task")

# Tool definition for Gemini function calling
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "add_task",
        "description": "Create a new task for the user",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The title of the task (required)"
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
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tags for the task"
                }
            },
            "required": ["title"]
        }
    }
}


def execute(
    db: Session,
    title: str,
    description: Optional[str] = None,
    priority: int = 0,
    due_date: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> dict:
    """
    Create a new task.

    Args:
        db: Database session
        title: Task title
        description: Task description
        priority: Priority level (0-3)
        due_date: Due date string (YYYY-MM-DD)
        tags: List of tags

    Returns:
        Dict with created task data
    """
    try:
        # Parse due_date if provided
        parsed_due_date = None
        if due_date:
            try:
                parsed_due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"Invalid due_date format: {due_date}")

        task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=parsed_due_date,
            tags=tags,
            completed=False,
            created_at=datetime.now(timezone.utc)
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        logger.info(f"Created task: {task.id} - {task.title}")

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
                "created_at": task.created_at.isoformat() if task.created_at else None
            }
        }

    except Exception as e:
        logger.error(f"Error creating task: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
