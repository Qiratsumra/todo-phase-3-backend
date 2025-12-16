"""
MCP Tool: delete_task - Delete a task permanently.
"""

from sqlalchemy.orm import Session
from models import Task
import logging

logger = logging.getLogger("mcp_tools.delete_task")

# Tool definition for Gemini function calling
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "delete_task",
        "description": "Delete a task permanently",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "ID of the task to delete"
                }
            },
            "required": ["task_id"]
        }
    }
}


def execute(db: Session, task_id: int) -> dict:
    """
    Delete a task permanently.

    Args:
        db: Database session
        task_id: ID of the task to delete

    Returns:
        Dict with deletion confirmation
    """
    try:
        task = db.query(Task).filter(Task.id == task_id).first()

        if not task:
            logger.warning(f"Task not found for deletion: {task_id}")
            return {
                "success": False,
                "error": f"Task with ID {task_id} not found"
            }

        title = task.title
        db.delete(task)
        db.commit()

        logger.info(f"Deleted task: {task_id} - {title}")

        return {
            "success": True,
            "message": f"Task '{title}' deleted successfully",
            "id": task_id
        }

    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
