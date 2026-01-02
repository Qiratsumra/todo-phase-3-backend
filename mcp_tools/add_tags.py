"""
MCP Tool: add_tags - Add tags to a task.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from models import Task
from datetime import datetime, timezone
from utils.validators import validate_tags, normalize_tags
import logging

logger = logging.getLogger("mcp_tools.add_tags")

# Tool definition for Gemini function calling
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "add_tags",
        "description": "Add tags to a task. Tags are additive - existing tags are preserved.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "ID of the task to add tags to"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to add (with or without # prefix)"
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
    Add tags to a task.

    Args:
        db: Database session
        task_id: ID of the task to add tags to
        tags: List of tags to add

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

        # Validate and normalize new tags
        is_valid, error, normalized_tags = validate_tags(tags)
        if not is_valid:
            return {
                "success": False,
                "error": error
            }

        # Merge with existing tags
        existing_tags = set(normalize_tags(old_tags))
        new_tags = set(normalized_tags)
        combined_tags = list(existing_tags.union(new_tags))

        # Update task
        task.tags = combined_tags
        db.commit()
        db.refresh(task)

        added_tags = [t for t in normalized_tags if t not in old_tags]

        logger.info(f"Added tags to task {task_id}: {added_tags}")

        return {
            "success": True,
            "task": {
                "id": task.id,
                "title": task.title,
                "tags": task.tags,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            },
            "added_tags": added_tags,
            "total_tags": len(task.tags),
        }

    except Exception as e:
        logger.error(f"Error adding tags to task: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
