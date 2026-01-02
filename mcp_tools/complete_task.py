"""
MCP Tool: complete_task - Mark a task as completed.
Supports recurring task completion with automatic next occurrence creation.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import Task
from datetime import datetime, timezone
from enums import RecurrenceEnum
from utils.recurrence_calculator import RecurrenceCalculator
import logging

logger = logging.getLogger("mcp_tools.complete_task")

# Tool definition for Gemini function calling
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "complete_task",
        "description": "Mark a task as completed. For recurring tasks, automatically creates the next occurrence.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "ID of the task to complete"
                },
                "create_next_occurrence": {
                    "type": "boolean",
                    "description": "Whether to create next occurrence for recurring tasks (default: true)"
                }
            },
            "required": ["task_id"]
        }
    }
}


def execute(
    db: Session,
    task_id: int,
    create_next_occurrence: bool = True
) -> dict:
    """
    Mark a task as completed.

    For recurring tasks, this will automatically create the next occurrence
    within 5 seconds of completion (as per the MVP requirement).

    Args:
        db: Database session
        task_id: ID of the task to complete
        create_next_occurrence: Whether to create next occurrence for recurring tasks

    Returns:
        Dict with updated task data and next occurrence info
    """
    try:
        task = db.query(Task).filter(Task.id == task_id).first()

        if not task:
            logger.warning(f"Task not found: {task_id}")
            return {
                "success": False,
                "error": f"Task with ID {task_id} not found"
            }

        if task.completed:
            logger.info(f"Task already completed: {task_id}")
            return {
                "success": False,
                "error": "Task is already completed",
                "task": {
                    "id": task.id,
                    "title": task.title,
                    "completed": task.completed
                }
            }

        # Store original task data for event publication
        original_task_data = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "due_date": str(task.due_date) if task.due_date else None,
            "tags": task.tags,
            "recurrence": task.recurrence.value if task.recurrence else None,
            "recurrence_pattern": task.recurrence_pattern,
        }

        # Mark task as completed
        task.completed = True
        task.completed_at = datetime.now(timezone.utc)

        # Check if this is a recurring task
        is_recurring = task.recurrence not in (None, RecurrenceEnum.NONE)
        next_occurrence = None

        if is_recurring and create_next_occurrence and task.recurrence_pattern:
            # Calculate next due date
            next_due_date = RecurrenceCalculator.calculate_next_due_date(
                task.due_date or datetime.now(timezone.utc),
                task.recurrence_pattern,
            )

            # Create next occurrence task
            next_task = Task(
                title=task.title,
                description=task.description,
                priority=task.priority,
                due_date=next_due_date.date() if next_due_date else None,
                tags=task.tags.copy(),
                completed=False,
                recurrence=task.recurrence,
                recurrence_pattern=task.recurrence_pattern,
                parent_task_id=task.id,
                created_at=datetime.now(timezone.utc),
            )

            db.add(next_task)
            db.commit()
            db.refresh(next_task)

            next_occurrence = {
                "id": next_task.id,
                "title": next_task.title,
                "due_date": str(next_task.due_date) if next_task.due_date else None,
                "created_at": next_task.created_at.isoformat() if next_task.created_at else None,
            }

            logger.info(
                f"Completed recurring task: {task.id} - {task.title}, "
                f"created next occurrence: {next_task.id} (due: {next_task.due_date})"
            )
        else:
            db.commit()
            logger.info(f"Completed task: {task.id} - {task.title}")

        db.refresh(task)

        result = {
            "success": True,
            "task": {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "completed": task.completed,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "priority": task.priority,
                "recurrence": task.recurrence.value if task.recurrence else None,
            },
            "is_recurring": is_recurring,
            "next_occurrence": next_occurrence,
        }

        # Add event publication data if recurring
        if is_recurring:
            result["event_data"] = {
                "task_id": task.id,
                "task_title": task.title,
                "is_recurring": True,
                "next_occurrence_id": next_occurrence["id"] if next_occurrence else None,
                "parent_task_id": task.id,
            }

        return result

    except Exception as e:
        logger.error(f"Error completing task {task_id}: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }


def complete_recurring_task(
    db: Session,
    task_id: int,
) -> dict:
    """
    Alias for complete_task with create_next_occurrence=True.

    This is an explicit version for when you want to emphasize
    that you're completing a recurring task.

    Args:
        db: Database session
        task_id: ID of the recurring task to complete

    Returns:
        Dict with completion results and next occurrence info
    """
    return execute(db, task_id, create_next_occurrence=True)
