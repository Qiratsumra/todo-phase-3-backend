"""Reminder Routes for Task Scheduling.

This module provides API endpoints for managing task reminders
using Dapr Jobs API for exact-time scheduling.

Endpoints:
- POST /api/reminders/ - Create a new reminder
- GET /api/reminders/{reminder_id} - Get reminder details
- DELETE /api/reminders/{reminder_id} - Cancel a reminder
- GET /api/reminders/task/{task_id} - Get reminders for a task
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import get_db
from models import Reminder, Task, ReminderStatusEnum, RecurrenceEnum
from schemas import parse_reminder_offset, VALID_REMINDER_OFFSETS
from utils.reminder_parser import parse_reminder_offset as parse_offset, ReminderParseResult
from services.dapr_jobs_client import get_dapr_jobs_client
from services.event_publisher import get_event_publisher

logger = logging.getLogger("app")

router = APIRouter()


# ========================================================================
# Pydantic Schemas
# ========================================================================

class ReminderCreateRequest(BaseModel):
    """Request schema for creating a reminder."""
    task_id: int
    offset_minutes: Optional[int] = Field(None, ge=5, le=10080)
    offset_string: Optional[str] = Field(None, description="Natural language offset like '30 minutes before'")
    scheduled_at: Optional[datetime] = Field(None, description="Exact scheduled time (overrides offset)")


class ReminderResponse(BaseModel):
    """Response schema for reminder data."""
    id: int
    task_id: int
    user_id: int
    scheduled_at: Optional[datetime]
    status: str
    dapr_job_id: Optional[str]
    offset_minutes: Optional[int]
    offset_string: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ReminderListResponse(BaseModel):
    """Response for listing reminders."""
    reminders: List[ReminderResponse]
    total_count: int


class CancelReminderResponse(BaseModel):
    """Response for cancelled reminder."""
    success: bool
    message: str
    reminder_id: int
    dapr_job_cancelled: bool


# ========================================================================
# Helper Functions
# ========================================================================

def _get_reminder_by_id(db: Session, reminder_id: int) -> Optional[Reminder]:
    """Get a reminder by ID."""
    return db.query(Reminder).filter(Reminder.id == reminder_id).first()


def _get_task_with_reminder_support(db: Session, task_id: int) -> Optional[Task]:
    """Get a task that supports reminders."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return None

    if not task.due_date:
        raise HTTPException(
            status_code=400,
            detail="Task must have a due date to set a reminder"
        )

    return task


async def _schedule_reminder_with_dapr(
    reminder: Reminder,
    task: Task,
    db: Session,
) -> tuple[bool, Optional[str]]:
    """Schedule a reminder using Dapr Jobs API.

    Args:
        reminder: The reminder to schedule
        task: The associated task
        db: Database session

    Returns:
        Tuple of (success, dapr_job_id)
    """
    try:
        client = get_dapr_jobs_client()

        # Build reminder data for the job payload
        reminder_data = {
            "task_title": task.title,
            "task_description": task.description or "",
            "priority": task.priority.value if task.priority else "medium",
            "offset_minutes": reminder.offset_minutes,
        }

        # Schedule the reminder
        success, job_id = await client.schedule_reminder(
            task_id=task.id,
            reminder_id=reminder.id,
            scheduled_at=reminder.scheduled_at,
            reminder_data=reminder_data,
        )

        if success and job_id:
            # Update reminder with Dapr job ID
            reminder.dapr_job_id = job_id
            db.commit()
            logger.info(f"Scheduled reminder {reminder.id} with Dapr job {job_id}")

        return success, job_id

    except Exception as e:
        logger.error(f"Error scheduling reminder with Dapr: {e}")
        return False, None


async def _publish_reminder_scheduled_event(
    reminder: Reminder,
    task: Task,
    dapr_job_id: Optional[str],
    db: Session,
) -> bool:
    """Publish reminder.scheduled event to Kafka.

    Args:
        reminder: The scheduled reminder
        task: The associated task
        dapr_job_id: Dapr Jobs API job ID
        db: Database session

    Returns:
        True if event was published successfully
    """
    try:
        publisher = get_event_publisher()

        # Build offset string for display
        offset_string = ""
        if reminder.offset_minutes:
            if reminder.offset_minutes < 60:
                offset_string = f"{reminder.offset_minutes} minutes before due"
            elif reminder.offset_minutes < 1440:
                hours = reminder.offset_minutes // 60
                offset_string = f"{hours} hour{'s' if hours != 1 else ''} before due"
            else:
                days = reminder.offset_minutes // 1440
                offset_string = f"{days} day{'s' if days != 1 else ''} before due"

        success = publisher.publish_reminder_scheduled(
            reminder_id=reminder.id,
            task_id=task.id,
            scheduled_at=reminder.scheduled_at.isoformat() if reminder.scheduled_at else None,
            reminder_offset=offset_string,
            dapr_job_id=dapr_job_id,
        )

        if success:
            logger.info(f"Published reminder.scheduled event for reminder {reminder.id}")

        return success

    except Exception as e:
        logger.error(f"Error publishing reminder.scheduled event: {e}")
        return False


# ========================================================================
# API Endpoints
# ========================================================================

@router.post("/reminders/", response_model=ReminderResponse)
async def create_reminder(
    request: ReminderCreateRequest,
    db: Session = Depends(get_db),
):
    """Create a new reminder for a task.

    The reminder will be scheduled using Dapr Jobs API to fire
    at the exact specified time.
    """
    # Validate task exists and has due date
    task = _get_task_with_reminder_support(db, request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Calculate scheduled time
    if request.scheduled_at:
        # Use exact time provided
        scheduled_at = request.scheduled_at
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

        # Validate it's in the future
        if scheduled_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=400,
                detail="Scheduled time must be in the future"
            )
    elif request.offset_minutes:
        # Calculate from due date
        if not task.due_date:
            raise HTTPException(
                status_code=400,
                detail="Task must have a due date to calculate reminder time"
            )

        # Use due_date with time if available, or start of day
        due_datetime = task.due_date
        if isinstance(due_datetime, date) and not isinstance(due_datetime, datetime):
            due_datetime = datetime.combine(due_datetime, datetime.min.time())
        if due_datetime.tzinfo is None:
            due_datetime = due_datetime.replace(tzinfo=timezone.utc)

        scheduled_at = due_datetime - timedelta(minutes=request.offset_minutes)

        # Validate it's in the future
        if scheduled_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=400,
                detail="Reminder time must be in the future"
            )
    elif request.offset_string:
        # Parse natural language offset
        parse_result = parse_offset(request.offset_string)
        if not parse_result.valid:
            raise HTTPException(
                status_code=400,
                detail=parse_result.error_message or "Invalid reminder offset"
            )

        if not task.due_date:
            raise HTTPException(
                status_code=400,
                detail="Task must have a due date to calculate reminder time"
            )

        # Calculate scheduled time
        due_datetime = task.due_date
        if isinstance(due_datetime, date) and not isinstance(due_datetime, datetime):
            due_datetime = datetime.combine(due_datetime, datetime.min.time())
        if due_datetime.tzinfo is None:
            due_datetime = due_datetime.replace(tzinfo=timezone.utc)

        scheduled_at = due_datetime - timedelta(minutes=parse_result.offset_minutes)
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide either scheduled_at, offset_minutes, or offset_string"
        )

    # Create reminder record
    reminder = Reminder(
        task_id=request.task_id,
        user_id=1,  # Single-user demo
        scheduled_at=scheduled_at,
        status=ReminderStatusEnum.PENDING,
        offset_minutes=request.offset_minutes or parse_result.offset_minutes if request.offset_string else None,
        offset_string=request.offset_string or parse_result.display_string if request.offset_string else None,
        created_at=datetime.now(timezone.utc),
    )

    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    logger.info(f"Created reminder {reminder.id} for task {task.id}")

    # Schedule with Dapr Jobs API
    dapr_job_id = None
    event_published = False

    try:
        success, dapr_job_id = await _schedule_reminder_with_dapr(reminder, task, db)
        if success and dapr_job_id:
            # Publish event to Kafka
            event_published = await _publish_reminder_scheduled_event(
                reminder, task, dapr_job_id, db
            )
        else:
            logger.warning(f"Failed to schedule reminder {reminder.id} with Dapr")
            # Mark reminder as failed if Dapr scheduling failed
            reminder.status = ReminderStatusEnum.FAILED
            db.commit()
    except Exception as e:
        logger.error(f"Error in reminder scheduling pipeline: {e}")
        # Continue but mark that Dapr scheduling failed
        reminder.status = ReminderStatusEnum.FAILED
        db.commit()

    return {
        "id": reminder.id,
        "task_id": reminder.task_id,
        "user_id": reminder.user_id,
        "scheduled_at": reminder.scheduled_at,
        "status": reminder.status.value if reminder.status else None,
        "dapr_job_id": reminder.dapr_job_id,
        "offset_minutes": reminder.offset_minutes,
        "offset_string": reminder.offset_string,
        "created_at": reminder.created_at,
        "dapr_job_scheduled": dapr_job_id is not None,
        "event_published": event_published,
    }


@router.get("/reminders/{reminder_id}")
async def get_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
):
    """Get reminder details."""
    reminder = _get_reminder_by_id(db, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    return {
        "id": reminder.id,
        "task_id": reminder.task_id,
        "user_id": reminder.user_id,
        "scheduled_at": reminder.scheduled_at.isoformat() if reminder.scheduled_at else None,
        "status": reminder.status.value if reminder.status else None,
        "dapr_job_id": reminder.dapr_job_id,
        "offset_minutes": reminder.offset_minutes,
        "offset_string": reminder.offset_string,
        "created_at": reminder.created_at.isoformat() if reminder.created_at else None,
    }


@router.delete("/reminders/{reminder_id}", response_model=CancelReminderResponse)
async def cancel_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
):
    """Cancel a pending reminder.

    Deletes the reminder record and cancels the Dapr Jobs API job if scheduled.
    """
    reminder = _get_reminder_by_id(db, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    if reminder.status == ReminderStatusEnum.CANCELLED:
        return {
            "success": True,
            "message": "Reminder was already cancelled",
            "reminder_id": reminder_id,
            "dapr_job_cancelled": False,
        }

    # Cancel Dapr job if exists
    dapr_job_cancelled = False
    if reminder.dapr_job_id:
        try:
            client = get_dapr_jobs_client()
            dapr_job_cancelled = await client.delete_job(reminder.dapr_job_id)
            if dapr_job_cancelled:
                logger.info(f"Cancelled Dapr job {reminder.dapr_job_id}")
        except Exception as e:
            logger.error(f"Error cancelling Dapr job: {e}")

    # Update reminder status
    reminder.status = ReminderStatusEnum.CANCELLED
    db.commit()

    logger.info(f"Cancelled reminder {reminder_id}")

    return {
        "success": True,
        "message": "Reminder cancelled successfully",
        "reminder_id": reminder_id,
        "dapr_job_cancelled": dapr_job_cancelled,
    }


@router.get("/reminders/task/{task_id}", response_model=ReminderListResponse)
async def get_task_reminders(
    task_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get all reminders for a task."""
    # Verify task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    query = db.query(Reminder).filter(Reminder.task_id == task_id)

    if status:
        try:
            query = query.filter(Reminder.status == ReminderStatusEnum(status))
        except ValueError:
            pass  # Invalid status, return all

    reminders = query.order_by(Reminder.scheduled_at.asc()).all()

    return {
        "reminders": [
            {
                "id": r.id,
                "task_id": r.task_id,
                "user_id": r.user_id,
                "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None,
                "status": r.status.value if r.status else None,
                "dapr_job_id": r.dapr_job_id,
                "offset_minutes": r.offset_minutes,
                "offset_string": r.offset_string,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reminders
        ],
        "total_count": len(reminders),
    }


@router.get("/reminders/pending")
async def get_pending_reminders(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Get all pending reminders."""
    query = db.query(Reminder).filter(Reminder.status == ReminderStatusEnum.PENDING)

    total_count = query.count()
    reminders = query.order_by(Reminder.scheduled_at.asc()).offset(offset).limit(limit).all()

    return {
        "reminders": [
            {
                "id": r.id,
                "task_id": r.task_id,
                "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None,
                "dapr_job_id": r.dapr_job_id,
                "offset_string": r.offset_string,
            }
            for r in reminders
        ],
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
    }
