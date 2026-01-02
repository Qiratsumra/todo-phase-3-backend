"""
MCP Tool: update_task_priority - Update task priority.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import Task, PriorityEnum
from datetime import datetime, timezone
import logging

logger = logging.getLogger("mcp_tools.update_task_priority")

# Tool definition for Gemini function calling
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "update_task_priority",
        "description": "Update the priority of a task (low, medium, or high)",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "ID of the task to update"
                },
                "priority": {
                    "type": "string",
                    "description": "New priority level",
                    "enum": ["low", "medium", "high"]
                }
            },
            "required": ["task_id", "priority"]
        }
    }
}


def execute(
    db: Session,
    task_id: int,
    priority: str,
) -> dict:
    """
    Update task priority.

    Args:
        db: Database session
        task_id: ID of the task to update
        priority: New priority (low, medium, high)

    Returns:
        Dict with updated task data
    """
    try:
        # Validate task exists
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {
                "success": False,
                "error": f"Task with ID {task_id} not found"
            }

        # Validate priority
        valid_priorities = ["low", "medium", "high"]
        if priority.lower() not in valid_priorities:
            return {
                "success": False,
                "error": f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"
            }

        old_priority = task.priority.value if task.priority else None
        task.priority = PriorityEnum(priority.lower())
        db.commit()
        db.refresh(task)

        logger.info(f"Updated task {task_id} priority: {old_priority} -> {priority}")

        return {
            "success": True,
            "task": {
                "id": task.id,
                "title": task.title,
                "priority": task.priority.value if task.priority else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            },
            "previous_priority": old_priority,
        }

    except Exception as e:
        logger.error(f"Error updating task priority: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
