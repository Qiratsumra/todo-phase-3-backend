"""
MCP Tool: list_tasks - Retrieve tasks with optional filtering.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from models import Task
import logging

logger = logging.getLogger("mcp_tools.list_tasks")

# Tool definition for Gemini function calling
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "list_tasks",
        "description": "Retrieve tasks with optional filtering by completion status",
        "parameters": {
            "type": "object",
            "properties": {
                "completed": {
                    "type": "boolean",
                    "description": "Filter by completion status (true=completed, false=pending, omit for all)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of tasks to return",
                    "default": 50
                }
            },
            "required": []
        }
    }
}


def execute(
    db: Session,
    completed: Optional[bool] = None,
    limit: int = 50
) -> dict:
    """
    List tasks with optional filtering.

    Args:
        db: Database session
        completed: Filter by completion status (None for all)
        limit: Maximum number of tasks

    Returns:
        Dict with list of tasks
    """
    try:
        query = db.query(Task)

        if completed is not None:
            query = query.filter(Task.completed == completed)

        tasks = query.order_by(Task.created_at.desc()).limit(limit).all()

        task_list = []
        for task in tasks:
            task_list.append({
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "completed": task.completed,
                "priority": task.priority,
                "due_date": str(task.due_date) if task.due_date else None,
                "tags": task.tags,
                "created_at": task.created_at.isoformat() if task.created_at else None
            })

        logger.info(f"Listed {len(task_list)} tasks")

        return {
            "success": True,
            "count": len(task_list),
            "tasks": task_list
        }

    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return {
            "success": False,
            "error": str(e)
        }
