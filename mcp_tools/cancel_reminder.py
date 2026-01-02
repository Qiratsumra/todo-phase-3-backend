"""
MCP Tool: cancel_reminder - Cancel a scheduled reminder.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import Reminder, ReminderStatusEnum
from datetime import datetime, timezone
import logging

logger = logging.getLogger("mcp_tools.cancel_reminder")

# Tool definition for Gemini function calling
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "cancel_reminder",
        "description": "Cancel a scheduled reminder. The reminder will be marked as cancelled and will not trigger.",
        "parameters": {
            "type": "object",
            "properties": {
                "reminder_id": {
                    "type": "integer",
                    "description": "ID of the reminder to cancel"
                }
            },
            "required": ["reminder_id"]
        }
    }
}


async def execute(  # Added async here
    db: Session,
    reminder_id: int,
) -> dict:
    """
    Cancel a scheduled reminder.

    Args:
        db: Database session
        reminder_id: ID of the reminder to cancel

    Returns:
        Dict with cancellation result
    """
    try:
        # Get reminder
        reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if not reminder:
            return {
                "success": False,
                "error": f"Reminder with ID {reminder_id} not found"
            }

        # Check if already cancelled or sent
        if reminder.status == ReminderStatusEnum.CANCELLED:
            return {
                "success": False,
                "error": "Reminder is already cancelled",
                "reminder": {
                    "id": reminder.id,
                    "status": reminder.status.value,
                }
            }

        if reminder.status == ReminderStatusEnum.SENT:
            return {
                "success": False,
                "error": "Reminder has already been sent and cannot be cancelled",
                "reminder": {
                    "id": reminder.id,
                    "status": reminder.status.value,
                }
            }

        # Cancel Dapr job if exists
        dapr_job_cancelled = False
        if reminder.dapr_job_id:
            try:
                from services.dapr_jobs_client import get_dapr_jobs_client
                client = get_dapr_jobs_client()
                dapr_job_cancelled = await client.delete_job(reminder.dapr_job_id)  # This now works because function is async
                if dapr_job_cancelled:
                    logger.info(f"Cancelled Dapr job {reminder.dapr_job_id}")
            except Exception as e:
                logger.warning(f"Failed to cancel Dapr job: {e}")

        # Update reminder status
        reminder.status = ReminderStatusEnum.CANCELLED
        db.commit()

        logger.info(f"Cancelled reminder {reminder_id}")

        return {
            "success": True,
            "message": "Reminder cancelled successfully",
            "reminder": {
                "id": reminder.id,
                "task_id": reminder.task_id,
                "scheduled_at": reminder.scheduled_at.isoformat() if reminder.scheduled_at else None,
                "status": reminder.status.value,
                "dapr_job_id": reminder.dapr_job_id,
            },
            "dapr_job_cancelled": dapr_job_cancelled,
        }

    except Exception as e:
        logger.error(f"Error cancelling reminder: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }