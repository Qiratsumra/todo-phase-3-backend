"""
MCP Tool: complete_task - Mark a task as completed.
"""

from sqlalchemy.orm import Session
from models import Task
import logging

logger = logging.getLogger("mcp_tools.complete_task")

# Tool definition for Gemini function calling
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "complete_task",
        "description": "Mark a task as completed",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "ID of the task to complete"
                }
            },
            "required": ["task_id"]
        }
    }
}


def execute(db: Session, task_id: int) -> dict:
    """
    Mark a task as completed.

    Args:
        db: Database session
        task_id: ID of the task to complete

    Returns:
        Dict with updated task data
    """
    try:
        task = db.query(Task).filter(Task.id == task_id).first()

        if not task:
            logger.warning(f"Task not found: {task_id}")
            return {
                "success": False,
                "error": f"Task with ID {task_id} not found"
            }

        task.completed = True
        db.commit()
        db.refresh(task)

        logger.info(f"Completed task: {task.id} - {task.title}")

        return {
            "success": True,
            "task": {
                "id": task.id,
                "title": task.title,
                "completed": task.completed,
                "priority": task.priority
            }
        }

    except Exception as e:
        logger.error(f"Error completing task {task_id}: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
