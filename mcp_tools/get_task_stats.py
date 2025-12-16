"""
MCP Tool: get_task_stats - Get task statistics for analytics.
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Task
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger("mcp_tools.get_task_stats")

# Tool definition for Gemini function calling
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_task_stats",
        "description": "Get aggregated task statistics for analytics",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to include in trends (default 7)",
                    "default": 7
                }
            },
            "required": []
        }
    }
}


def execute(db: Session, days: int = 7) -> dict:
    """
    Get task statistics.

    Args:
        db: Database session
        days: Number of days for trend data

    Returns:
        Dict with task statistics
    """
    try:
        # Total counts
        total_tasks = db.query(func.count(Task.id)).scalar() or 0
        completed_tasks = db.query(func.count(Task.id)).filter(Task.completed == True).scalar() or 0
        pending_tasks = total_tasks - completed_tasks

        # Completion rate
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Overdue tasks (due_date < today and not completed)
        today = datetime.now(timezone.utc).date()
        overdue_tasks = db.query(func.count(Task.id)).filter(
            Task.due_date < today,
            Task.completed == False
        ).scalar() or 0

        # High priority pending
        high_priority_pending = db.query(func.count(Task.id)).filter(
            Task.priority == 3,
            Task.completed == False
        ).scalar() or 0

        # Tasks by day (last N days)
        tasks_by_day = []
        for i in range(days - 1, -1, -1):
            day = datetime.now(timezone.utc) - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

            created = db.query(func.count(Task.id)).filter(
                Task.created_at >= day_start,
                Task.created_at <= day_end
            ).scalar() or 0

            # Note: We don't have completed_at field, so we estimate based on completion status
            # In a real app, you'd want a completed_at timestamp
            tasks_by_day.append({
                "date": day.strftime("%Y-%m-%d"),
                "created": created,
                "completed": 0  # Would need completed_at field
            })

        # Priority distribution
        priority_distribution = {
            "none": db.query(func.count(Task.id)).filter(Task.priority == 0).scalar() or 0,
            "low": db.query(func.count(Task.id)).filter(Task.priority == 1).scalar() or 0,
            "medium": db.query(func.count(Task.id)).filter(Task.priority == 2).scalar() or 0,
            "high": db.query(func.count(Task.id)).filter(Task.priority == 3).scalar() or 0
        }

        logger.info(f"Generated stats: {total_tasks} total, {completion_rate:.1f}% complete")

        return {
            "success": True,
            "stats": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "pending_tasks": pending_tasks,
                "completion_rate": round(completion_rate, 1),
                "overdue_tasks": overdue_tasks,
                "high_priority_pending": high_priority_pending,
                "priority_distribution": priority_distribution,
                "tasks_by_day": tasks_by_day
            }
        }

    except Exception as e:
        logger.error(f"Error getting task stats: {e}")
        return {
            "success": False,
            "error": str(e)
        }
