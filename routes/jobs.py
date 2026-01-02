"""Dapr Jobs API Trigger Endpoint.

This module provides the callback endpoint for Dapr Jobs API.
When a scheduled job triggers, Dapr sends a callback to this endpoint.

Dapr Jobs API callback:
- POST /api/jobs/trigger
- Dapr sends job data in request body
- We process the trigger and publish reminder events

Reference: https://docs.dapr.io/reference/api/job-api/
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from models import Reminder, ReminderStatusEnum, Task
from services.event_publisher import get_event_publisher
from services.dapr_jobs_client import JobTriggerHandler

logger = logging.getLogger("app")

router = APIRouter()


@router.post("/api/jobs/trigger")
async def trigger_job(
    request: Request,
    job_data: Dict[str, Any] = None,
):
    """Handle Dapr Jobs API trigger callback.

    When a scheduled reminder job fires, Dapr calls this endpoint
    with the job data. We process the trigger and publish events.

    Args:
        request: FastAPI request object
        job_data: Job payload from Dapr (optional, can also be in request body)

    Returns:
        Response with status and action taken
    """
    try:
        # Get job data from request body or form data
        if job_data is None:
            try:
                job_data = await request.json()
            except Exception:
                # Try form data
                form_data = await request.form()
                job_data = dict(form_data)

        logger.info(f"Received Dapr job trigger: {job_data}")

        # Validate job type
        job_type = job_data.get("type")
        if job_type != "reminder":
            logger.warning(f"Ignoring unknown job type: {job_type}")
            return {
                "status": "ignored",
                "reason": "unknown_job_type",
                "job_type": job_type,
            }

        # Extract reminder data
        reminder_id = job_data.get("reminder_id")
        task_id = job_data.get("task_id")
        scheduled_at = job_data.get("scheduled_at")

        if not reminder_id or not task_id:
            logger.error(f"Missing required fields in job data: reminder_id={reminder_id}, task_id={task_id}")
            return {
                "status": "error",
                "reason": "missing_required_fields",
            }

        # Get database session
        db = next(get_db())

        try:
            # Get reminder record
            reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
            if not reminder:
                logger.warning(f"Reminder not found: {reminder_id}")
                return {
                    "status": "ignored",
                    "reason": "reminder_not_found",
                    "reminder_id": reminder_id,
                }

            # Check if already processed
            if reminder.status in [ReminderStatusEnum.SENT, ReminderStatusEnum.CANCELLED, ReminderStatusEnum.FAILED]:
                logger.info(f"Reminder {reminder_id} already in status: {reminder.status}")
                return {
                    "status": "ignored",
                    "reason": "already_processed",
                    "reminder_id": reminder_id,
                    "current_status": reminder.status.value,
                }

            # Get task info
            task = db.query(Task).filter(Task.id == task_id).first()
            task_title = task.title if task else "Unknown Task"

            # Mark reminder as triggered
            reminder.status = ReminderStatusEnum.PENDING  # Ready to be processed
            db.commit()

            # Publish reminder.triggered event to Kafka
            publisher = get_event_publisher()
            event_success = publisher.publish_reminder_triggered(
                reminder_id=reminder_id,
                task_id=task_id,
                scheduled_at=scheduled_at or datetime.now(timezone.utc).isoformat(),
            )

            if event_success:
                # Update reminder status to indicate event was published
                # The notification service will consume and mark as SENT
                logger.info(f"Published reminder.triggered event for reminder {reminder_id}")
                return {
                    "status": "processed",
                    "action": "reminder_triggered",
                    "reminder_id": reminder_id,
                    "task_id": task_id,
                    "task_title": task_title,
                    "event_published": True,
                }
            else:
                logger.error(f"Failed to publish reminder.triggered event for reminder {reminder_id}")
                return {
                    "status": "error",
                    "action": "failed_to_publish_event",
                    "reminder_id": reminder_id,
                    "event_published": False,
                }

        except Exception as e:
            db.rollback()
            logger.error(f"Error processing job trigger: {e}")
            raise
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error handling Dapr job trigger: {e}")
        raise HTTPException(status_code=500, detail="Error processing job trigger")


@router.get("/api/jobs/health")
async def jobs_health_check():
    """Health check endpoint for Dapr Jobs API integration."""
    return {
        "status": "ok",
        "service": "jobs-trigger-handler",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/api/jobs/schedule-test")
async def schedule_test_job(
    request: Request,
):
    """Schedule a test job for verification purposes.

    This endpoint is for testing the Dapr Jobs API integration.
    It creates a reminder that fires in 1 minute.
    """
    from datetime import timedelta

    try:
        data = await request.json()
        task_id = data.get("task_id", 1)
        db = next(get_db())

        # Create a test reminder that fires in 1 minute
        scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=1)

        reminder = Reminder(
            task_id=task_id,
            user_id=1,
            scheduled_at=scheduled_at,
            status=ReminderStatusEnum.PENDING,
            offset_minutes=1,
            offset_string="1 minute before due (test)",
            created_at=datetime.now(timezone.utc),
        )

        db.add(reminder)
        db.commit()
        db.refresh(reminder)

        # Schedule with Dapr
        client = get_dapr_jobs_client()
        success, job_id = await client.schedule_reminder(
            task_id=task_id,
            reminder_id=reminder.id,
            scheduled_at=scheduled_at,
            reminder_data={
                "task_title": "Test Reminder",
                "test": True,
            },
        )

        if success and job_id:
            reminder.dapr_job_id = job_id
            db.commit()

            return {
                "success": True,
                "reminder_id": reminder.id,
                "dapr_job_id": job_id,
                "scheduled_at": scheduled_at.isoformat(),
                "message": f"Test reminder scheduled to fire at {scheduled_at.isoformat()}",
            }
        else:
            db.delete(reminder)
            db.commit()
            return {
                "success": False,
                "error": "Failed to schedule with Dapr",
            }

    except Exception as e:
        logger.error(f"Error scheduling test job: {e}")
        raise HTTPException(status_code=500, detail=str(e))
