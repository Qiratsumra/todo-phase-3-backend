"""
MCP Tool: search_tasks - Advanced task search with filters.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from models import Task
from datetime import datetime
import logging

logger = logging.getLogger("mcp_tools.search_tasks")

# Tool definition for Gemini function calling
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_tasks",
        "description": "Advanced task search by keyword, status, priority, and date range",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Search keyword to find in title or description"
                },
                "completed": {
                    "type": "boolean",
                    "description": "Filter by completion status"
                },
                "priority": {
                    "type": "integer",
                    "description": "Filter by priority level",
                    "enum": [0, 1, 2, 3]
                },
                "date_from": {
                    "type": "string",
                    "description": "Filter tasks created on or after this date (YYYY-MM-DD)"
                },
                "date_to": {
                    "type": "string",
                    "description": "Filter tasks created on or before this date (YYYY-MM-DD)"
                },
                "due_before": {
                    "type": "string",
                    "description": "Filter tasks due on or before this date (YYYY-MM-DD)"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter tasks containing any of these tags"
                }
            },
            "required": []
        }
    }
}


def execute(
    db: Session,
    keyword: Optional[str] = None,
    completed: Optional[bool] = None,
    priority: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    due_before: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> dict:
    """
    Search tasks with advanced filters.

    Args:
        db: Database session
        keyword: Search term for title/description
        completed: Filter by completion status
        priority: Filter by priority level
        date_from: Filter by creation date (from)
        date_to: Filter by creation date (to)
        due_before: Filter by due date
        tags: Filter by tags

    Returns:
        Dict with matching tasks
    """
    try:
        query = db.query(Task)

        # Keyword search in title and description
        if keyword:
            keyword_filter = f"%{keyword.lower()}%"
            query = query.filter(
                or_(
                    Task.title.ilike(keyword_filter),
                    Task.description.ilike(keyword_filter)
                )
            )

        # Completion status filter
        if completed is not None:
            query = query.filter(Task.completed == completed)

        # Priority filter
        if priority is not None:
            query = query.filter(Task.priority == priority)

        # Date range filters
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(Task.created_at >= from_date)
            except ValueError:
                logger.warning(f"Invalid date_from format: {date_from}")

        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d")
                query = query.filter(Task.created_at <= to_date)
            except ValueError:
                logger.warning(f"Invalid date_to format: {date_to}")

        if due_before:
            try:
                due_date = datetime.strptime(due_before, "%Y-%m-%d").date()
                query = query.filter(Task.due_date <= due_date)
            except ValueError:
                logger.warning(f"Invalid due_before format: {due_before}")

        # Tag filter (any match)
        if tags:
            query = query.filter(Task.tags.overlap(tags))

        tasks = query.order_by(Task.created_at.desc()).all()

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

        logger.info(f"Search found {len(task_list)} tasks")

        return {
            "success": True,
            "count": len(task_list),
            "tasks": task_list
        }

    except Exception as e:
        logger.error(f"Error searching tasks: {e}")
        return {
            "success": False,
            "error": str(e)
        }
