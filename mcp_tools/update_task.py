"""
MCP Tool: update_task - Update task attributes.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from models import Task
from datetime import datetime
import logging

logger = logging.getLogger("mcp_tools.update_task")

# Tool definition for Gemini function calling
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "update_task",
        "description": "Update one or more attributes of a task",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "ID of the task to update"
                },
                "title": {
                    "type": "string",
                    "description": "New title for the task"
                },
                "description": {
                    "type": "string",
                    "description": "New description"
                },
                "priority": {
                    "type": "integer",
                    "description": "New priority level",
                    "enum": [0, 1, 2, 3]
                },
                "due_date": {
                    "type": "string",
                    "description": "New due date in YYYY-MM-DD format"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New tags list"
                },
                "completed": {
                    "type": "boolean",
                    "description": "New completion status"
                }
            },
            "required": ["task_id"]
        }
    }
}


def execute(
    db: Session,
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[int] = None,
    due_date: Optional[str] = None,
    tags: Optional[List[str]] = None,
    completed: Optional[bool] = None
) -> dict:
    """
    Update task attributes.

    Args:
        db: Database session
        task_id: ID of the task to update
        title: New title
        description: New description
        priority: New priority
        due_date: New due date (YYYY-MM-DD)
        tags: New tags
        completed: New completion status

    Returns:
        Dict with updated task data
    """
    try:
        task = db.query(Task).filter(Task.id == task_id).first()

        if not task:
            logger.warning(f"Task not found for update: {task_id}")
            return {
                "success": False,
                "error": f"Task with ID {task_id} not found"
            }

        # Update only provided fields
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = priority
        if tags is not None:
            task.tags = tags
        if completed is not None:
            task.completed = completed
        if due_date is not None:
            try:
                task.due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"Invalid due_date format: {due_date}")

        db.commit()
        db.refresh(task)

        logger.info(f"Updated task: {task.id} - {task.title}")

        return {
            "success": True,
            "task": {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "completed": task.completed,
                "priority": task.priority,
                "due_date": str(task.due_date) if task.due_date else None,
                "tags": task.tags
            }
        }

    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
