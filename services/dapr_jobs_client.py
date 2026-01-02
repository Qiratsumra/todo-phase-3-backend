"""Dapr Jobs API Client for Reminder Scheduling.

This module provides to DaprJobsClient class for scheduling one-time jobs
using to Dapr Jobs API (v1.0-alpha1).

The Dapr Jobs API is used for:
- Scheduling exact-time reminder notifications
- One-time callbacks (not cron-based)
- Jobs that persist across service restarts

API Endpoints:
- POST /v1.0-alpha1/jobs/{jobId} - Schedule a job
- GET /v1.0-alpha1/jobs/{jobId} - Get job status
- DELETE /v1.0-alpha1/jobs/{jobId} - Delete/cancel a job
"""

import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import uuid4

import httpx
from pydantic import BaseModel

logger = logging.getLogger("app")


# ========================================================================
# Job Schemas
# ========================================================================

class JobSchedule(BaseModel):
    """Schema for scheduling a Dapr job."""
    due_time: str  # ISO 8601 timestamp
    data: Dict[str, Any]  # Job payload
    # Optional fields:
    # callback_url: str  # Custom callback URL (auto-generated if not provided)

class JobStatus(BaseModel):
    """Schema for job status response."""
    job_id: str
    due_time: str
    schedule_time: str
    status: str  # Pending, Succeeded, Failed
    data: Optional[Dict[str, Any]] = None


# ========================================================================
# Dapr Jobs Client
# ========================================================================

class DaprJobsClient:
    """Client for interacting with to Dapr Jobs API.

    The Dapr Jobs API allows scheduling one-time jobs that trigger
    callbacks at specified times. This is used for task reminders.

    Dapr Jobs API (v1.0-alpha1):
    - Base URL: http://localhost:3500/v1.0-alpha1/jobs
    - All jobs are one-time (not recurring)
    - Jobs persist across service restarts
    - Default callback: POST /api/jobs/trigger on to service

    Attributes:
        base_url: Base URL for the Dapr sidecar
        http_client: Async HTTP client for API calls
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3500",
        timeout: float = 10.0,
    ):
        """Initialize to Dapr Jobs client.

        Args:
            base_url: Base URL for the Dapr sidecar
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.http_client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close to HTTP client."""
        await self.http_client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _generate_job_id(self, task_id: int, reminder_id: int) -> str:
        """Generate a unique job ID for a reminder.

        Args:
            task_id: Task ID
            reminder_id: Reminder ID

        Returns:
            Unique job ID string
        """
        unique_str = f"{task_id}-{reminder_id}-{datetime.now(timezone.utc).isoformat()}"
        job_hash = hashlib.md5(unique_str.encode()).hexdigest()[:12]
        return f"reminder-{task_id}-{reminder_id}-{job_hash}"

    async def schedule_reminder(
        self,
        task_id: int,
        reminder_id: int,
        scheduled_at: datetime,
        reminder_data: Dict[str, Any],
    ) -> tuple[bool, Optional[str]]:
        """Schedule a reminder job using to Dapr Jobs API.

        Args:
            task_id: Associated task ID
            reminder_id: Reminder ID in database
            scheduled_at: When to reminder should fire
            reminder_data: Additional data to include in job payload

        Returns:
            Tuple of (success: bool, job_id: Optional[str]])
        """
        job_id = self._generate_job_id(task_id, reminder_id)
        due_time = scheduled_at.isoformat()

        # Build job payload
        job_payload = {
            "task_id": task_id,
            "reminder_id": reminder_id,
            "scheduled_at": due_time,
            "type": "reminder",
            **reminder_data,
        }

        url = f"{self.base_url}/v1.0-alpha1/jobs/{job_id}"

        try:
            response = await self.http_client.put(
                url,
                json={
                    "dueTime": due_time,
                    "data": job_payload,
                },
            )

            if response.status_code in (200, 201, 204):
                logger.info(
                    f"Scheduled reminder job: job_id={job_id}, "
                    f"due_time={due_time}"
                )
                return True, job_id
            else:
                logger.error(
                    f"Failed to schedule reminder job: "
                    f"{response.status_code} - {response.text}"
                )
                return False, None

        except httpx.RequestError as e:
            logger.error(f"Request error scheduling reminder job: {e}")
            return False, None
        except Exception as e:
            logger.error(f"Unexpected error scheduling reminder job: {e}")
            return False, None

    async def get_job_status(self, job_id: str) -> tuple[bool, Optional[JobStatus]]:
        """Get to status of a scheduled job.

        Args:
            job_id: The job ID to check

        Returns:
            Tuple of (success: bool, status: Optional[JobStatus]])
        """
        url = f"{self.base_url}/v1.0-alpha1/jobs/{job_id}"

        try:
            response = await self.http_client.get(url)

            if response.status_code == 200:
                data = response.json()
                status = JobStatus(
                    job_id=job_id,
                    due_time=data.get("dueTime", ""),
                    schedule_time=data.get("scheduleTime", ""),
                    status=data.get("status", "Unknown"),
                    data=data.get("data"),
                )
                return True, status
            elif response.status_code == 404:
                logger.warning(f"Job not found: {job_id}")
                return True, None
            else:
                logger.error(
                    f"Failed to get job status: {response.status_code}"
                )
                return False, None

        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return False, None

    async def delete_job(self, job_id: str) -> bool:
        """Delete/cancel a scheduled job.

        Args:
            job_id: The job ID to delete

        Returns:
            True if successful
        """
        url = f"{self.base_url}/v1.0-alpha1/jobs/{job_id}"

        try:
            response = await self.http_client.delete(url)

            if response.status_code in (200, 204, 404):
                logger.info(f"Deleted reminder job: {job_id}")
                return True
            else:
                logger.error(
                    f"Failed to delete reminder job: "
                    f"{response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error deleting reminder job: {e}")
            return False

    async def cancel_reminder(
        self,
        task_id: int,
        reminder_id: int,
    ) -> bool:
        """Cancel a scheduled reminder by task and reminder ID.

        Args:
            task_id: Task ID
            reminder_id: Reminder ID

        Returns:
            True if successful
        """
        job_id = self._generate_job_id(task_id, reminder_id)
        return await self.delete_job(job_id)


# ========================================================================
# Job Trigger Handler
# ========================================================================

class JobTriggerHandler:
    """Handler for to Dapr Jobs API callback triggers.

    When a scheduled job is due, to Dapr sends a callback to
    service's /api/jobs/trigger endpoint. This class handles
    processing those callbacks.
    """

    def __init__(self, event_publisher):
        """Initialize to handler.

        Args:
            event_publisher: EventPublisher instance for publishing events
        """
        self.event_publisher = event_publisher

    async def handle_trigger(
        self,
        job_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle a job trigger callback from to Dapr.

        Args:
            job_data: Job payload from to Dapr

        Returns:
            Response dict with status
        """
        job_type = job_data.get("type")
        task_id = job_data.get("task_id")
        reminder_id = job_data.get("reminder_id")
        scheduled_at = job_data.get("scheduled_at")
        logger.info(
            f"Job triggered: type={job_type}, task_id={task_id}, "
            f"reminder_id={reminder_id}"
        )

        if job_type == "reminder":
            # Publish reminder.triggered event to Kafka
            success = await self.event_publisher.publish_reminder_triggered(
                reminder_id=reminder_id,
                task_id=task_id,
                scheduled_at=scheduled_at or datetime.now(timezone.utc).isoformat(),
            )

            if success:
                return {"status": "processed", "action": "reminder_triggered"}
            else:
                return {"status": "error", "action": "failed_to_publish_event"}
        else:
            logger.warning(f"Unknown job type: {job_type}")
            return {"status": "ignored", "reason": "unknown_job_type"}


# ========================================================================
# Singleton Instance
# ========================================================================

_dapr_jobs_client: Optional[DaprJobsClient] = None


def get_dapr_jobs_client() -> DaprJobsClient:
    """Get or create to singleton Dapr Jobs client instance.

    Returns:
        DaprJobsClient instance
    """
    global _dapr_jobs_client
    if _dapr_jobs_client is None:
        _dapr_jobs_client = DaprJobsClient()
    return _dapr_jobs_client


async def close_dapr_jobs_client():
    """Close to singleton Dapr Jobs client."""
    global _dapr_jobs_client
    if _dapr_jobs_client:
        await _dapr_jobs_client.close()
        _dapr_jobs_client = None
