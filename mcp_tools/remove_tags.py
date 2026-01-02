"""
MCP Tool: remove_tags - Remove tags from a task.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from models import Task
from datetime import datetime, timezone
from utils.validators import normalize_tags, remove_tags as remove_tags_util
import logging

logger = logging.getLogger("mcp_tools.remove_tags")

# Tool definition for Gemini function calling
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "remove_tags",
        "description": "Remove tags from a task. Only removes tags that exist on the task.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "ID of the task to remove tags from"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to remove (with or without # prefix)"
                }
            },
            "required": ["task_id", "tags"]
        }
    }
}


def execute(
    db: Session,
    task_id: int,
    tags: List[str],
) -> dict:
    """
    Remove tags from a task.

    Args:
        db: Database session
        task_id: ID of the task to remove tags from
        tags: List of tags to remove

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

        # Store old tags for response
        old_tags = task.tags.copy() if task.tags else []

        if not old_tags:
            return {
                "success": False,
                "error": "Task has no tags to remove"
            }

        # Normalize tags to remove
        tags_to_remove = normalize_tags(tags)

        # Calculate remaining tags
        remaining_tags = remove_tags_util(old_tags, tags_to_remove)

        # Find which tags were actually removed
        removed = [t for t in tags_to_remove if t in old_tags and t not in remaining_tags]
        not_found = [t for t in tags_to_remove if t not in old_tags]

        # Update task
        task.tags = remaining_tags
        db.commit()
        db.refresh(task)

        logger.info(f"Removed tags from task {task_id}: {removed}")

        result = {
            "success": True,
            "task": {
                "id": task.id,
                "title": task.title,
                "tags": task.tags,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            },
            "removed_tags": removed,
            "total_tags": len(task.tags),
        }

        if not_found:
            result["warnings"] = [f"Tag '{t}' not found on task" for t in not_found]

        return result

    except Exception as e:
        logger.error(f"Error removing tags from task: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
