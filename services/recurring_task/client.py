# ========================================================================
# Backend API Client via Dapr Service Invocation
# ========================================================================

import logging
from typing import Optional

from dapr.clients import DaprClient

logger = logging.getLogger(__name__)


class BackendAPIClient:
    """Calls Backend API via Dapr Service Invocation."""

    APP_ID = "taskflow-backend"
    METHOD_CREATE_TASK = "create_task"

    def __init__(self, dapr_client: DaprClient):
        self.dapr_client = dapr_client

    async def create_next_occurrence(
        self,
        user_id: str,
        title: str,
        description: Optional[str],
        priority: str,
        due_date: str,
        recurrence: str,
        parent_task_id: int
    ) -> bool:
        """Create next occurrence via Dapr service invocation."""
        payload = {
            "user_id": user_id,
            "title": title,
            "description": description,
            "priority": priority,
            "due_date": due_date,
            "recurrence": recurrence,
            "metadata": {
                "parent_task_id": str(parent_task_id),
                "created_by": "recurring-task-service",
                "auto_generated": True
            }
        }

        try:
            response = self.dapr_client.invoke_method(
                app_id=self.APP_ID,
                method=self.METHOD_CREATE_TASK,
                data=payload,
                content_type="application/json",
                http_verb="POST"
            )
            return response and response.status_code in (200, 201)
        except Exception as e:
            logger.error(f"Error creating next occurrence: {e}")
            return False
