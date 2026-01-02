"""Task CRUD service with Phase V enhanced features.

This module provides the TaskService class for managing tasks with
support for priorities, tags, recurrence patterns, and reminders.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, text
from pydantic import BaseModel

from database import get_db
from models import Task, Reminder, AuditLogEntry, RecurrenceEnum, PriorityEnum, TaskStatusEnum, Comment, Attachment, Project
from schemas import (
    TaskCreate, TaskUpdate, TaskResponse, TaskListResponse,
    UpdatePriorityRequest, AddTagsRequest, RemoveTagsRequest,
    TaskFilter, TaskSort, SortOrder, TaskSearchRequest, TaskSearchResponse,
    SubtaskCreate, SubtaskResponse, CommentCreate, CommentResponse,
    AttachmentCreate, AttachmentResponse,
    VALID_REMINDER_OFFSETS, parse_reminder_offset,
    ProjectCreate, ProjectResponse,
)
from enums import get_priority_weight
from utils.recurrence_calculator import RecurrenceCalculator

logger = logging.getLogger("app")

router = APIRouter()


class ProjectService:
    """Service class for project CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_projects(self) -> List[ProjectResponse]:
        """Get all projects."""
        projects = self.db.query(Project).all()
        return [ProjectResponse.from_orm(p) for p in projects]

    def create_project(self, project_data: ProjectCreate) -> ProjectResponse:
        """Create a new project."""
        db_project = Project(name=project_data.name)
        self.db.add(db_project)
        self.db.commit()
        self.db.refresh(db_project)
        return ProjectResponse.from_orm(db_project)


class TaskService:
    """Service class for task CRUD operations with Phase V enhancements."""

    def __init__(self, db: Session):
        self.db = db

    def create_comment_for_task(self, task_id: int, comment_data: CommentCreate) -> CommentResponse:
        """Create a new comment for a task."""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        db_comment = Comment(
            content=comment_data.content,
            task_id=task_id,
        )
        self.db.add(db_comment)
        self.db.commit()
        self.db.refresh(db_comment)

        logger.info(f"Created comment {db_comment.id} for task {task_id}")
        return CommentResponse.from_orm(db_comment)

    def create_attachment_for_task(self, task_id: int, attachment_data: AttachmentCreate) -> AttachmentResponse:
        """Create a new attachment for a task."""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        db_attachment = Attachment(
            file_name=attachment_data.file_name,
            file_url=attachment_data.file_url,
            task_id=task_id,
        )
        self.db.add(db_attachment)
        self.db.commit()
        self.db.refresh(db_attachment)

        logger.info(f"Created attachment {db_attachment.id} for task {task_id}")
        return AttachmentResponse.from_orm(db_attachment)

    def create_subtask(self, parent_task_id: int, subtask_data: SubtaskCreate) -> SubtaskResponse:
        """Create a new subtask for a parent task."""
        parent_task = self.db.query(Task).filter(Task.id == parent_task_id).first()
        if not parent_task:
            raise HTTPException(status_code=404, detail="Parent task not found")

        db_subtask = Task(
            title=subtask_data.title,
            description=subtask_data.description,
            priority=PriorityEnum(subtask_data.priority.value),
            due_date=subtask_data.due_date,
            parent_task_id=parent_task_id,
        )
        self.db.add(db_subtask)
        self.db.commit()
        self.db.refresh(db_subtask)

        logger.info(f"Created subtask {db_subtask.id} for parent {parent_task_id}")
        return SubtaskResponse.from_orm(db_subtask)

    # ========================================================================
    # Basic CRUD Operations
    # ========================================================================

    def get_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        tags: Optional[List[str]] = None,
        due_before: Optional[datetime] = None,
        due_after: Optional[datetime] = None,
        sort_by: str = "created_at",
        order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> TaskListResponse:
        """Get tasks with optional filtering and sorting.

        Args:
            status: Filter by task status (pending/completed)
            priority: Filter by priority (low/medium/high)
            tags: Filter by tags (tasks containing any of the tags)
            due_before: Filter tasks due before this time
            due_after: Filter tasks due after this time
            sort_by: Field to sort by (created_at, due_date, priority, title)
            order: Sort order (asc, desc)
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip

        Returns:
            TaskListResponse with tasks and total count
        """
        try:
            query = self.db.query(Task)

            # Apply filters
            if status:
                query = query.filter(Task.status == TaskStatusEnum(status))

            if priority:
                query = query.filter(Task.priority == PriorityEnum(priority))

            if tags:
                # Use PostgreSQL array containment for tag filtering
                # Tags must contain at least one of the specified tags
                query = query.filter(Task.tags.contains(tags))

            if due_before:
                query = query.filter(Task.due_date <= due_before)

            if due_after:
                query = query.filter(Task.due_date >= due_after)

            # Filter for top-level tasks only
            query = query.filter(Task.parent_task_id.is_(None))

            # Get total count before pagination
            total_count = query.count()

            # Apply sorting
            sort_column = getattr(Task, sort_by, Task.created_at)

            if order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

            # Apply pagination
            tasks = query.offset(offset).limit(limit).all()

            # Convert to response format
            task_responses = [
                TaskResponse.from_orm(task) for task in tasks
            ]

            return TaskListResponse(
                tasks=task_responses,
                total_count=total_count,
                page=offset // limit + 1,
                page_size=limit,
            )

        except Exception as e:
            logger.error(f"Error retrieving tasks: {e}")
            raise HTTPException(status_code=500, detail="Error retrieving tasks")

    def get_task(self, task_id: int) -> TaskResponse:
        """Get a single task by ID, including its subtasks.

        Args:
            task_id: The task ID to retrieve

        Returns:
            TaskResponse with task details and subtasks

        Raises:
            HTTPException: If task not found
        """
        try:
            task = self.db.query(Task).options(
                joinedload(Task.children),
                joinedload(Task.comments),
                joinedload(Task.attachments)
            ).filter(Task.id == task_id).first()

            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            return TaskResponse.from_orm(task)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving task {task_id}: {e}")
            raise HTTPException(status_code=500, detail="Error retrieving task")

    def create_task(self, task_data: TaskCreate) -> TaskResponse:
        """Create a new task.

        Args:
            task_data: Task creation data

        Returns:
            TaskResponse with created task
        """
        try:
            # Convert string enums to enum types
            recurrence = RecurrenceEnum(task_data.recurrence.value if hasattr(task_data.recurrence, 'value') else task_data.recurrence)
            priority = PriorityEnum(task_data.priority.value if hasattr(task_data.priority, 'value') else task_data.priority)

            # Validate and format tags
            tags = []
            for tag in (task_data.tags or []):
                if not tag.startswith('#'):
                    tag = f'#{tag}'
                tags.append(tag)

            db_task = Task(
                title=task_data.title,
                description=task_data.description,
                priority=priority,
                tags=tags,
                due_date=task_data.due_date,
                recurrence=recurrence,
            )
            self.db.add(db_task)
            self.db.commit()
            self.db.refresh(db_task)

            # Create audit log entry
            self._create_audit_entry(
                event_type="task.created",
                task_id=db_task.id,
                event_data=db_task.to_dict(),
            )

            logger.info(f"Created task: {db_task.id} - {db_task.title}")
            return TaskResponse.from_orm(db_task)

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating task: {e}")
            raise HTTPException(status_code=500, detail="Error creating task")

    def update_task(self, task_id: int, task_update: TaskUpdate) -> TaskResponse:
        """Update a task (partial update).

        Args:
            task_id: The task ID to update
            task_update: Update data

        Returns:
            TaskResponse with updated task

        Raises:
            HTTPException: If task not found
        """
        try:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            # Track changes for audit
            old_data = task.to_dict()

            # Update fields that were provided
            update_data = task_update.dict(exclude_unset=True)

            for field, value in update_data.items():
                if field == 'priority' and value:
                    value = PriorityEnum(value.value if hasattr(value, 'value') else value)
                elif field == 'recurrence' and value:
                    value = RecurrenceEnum(value.value if hasattr(value, 'value') else value)
                elif field == 'tags' and value:
                    # Validate and format tags
                    tags = []
                    for tag in value:
                        if not tag.startswith('#'):
                            tag = f'#{tag}'
                        tags.append(tag)
                    value = tags
                elif field == 'completed' and value is not None:
                    # Handle status change
                    task.status = TaskStatusEnum.COMPLETED if value else TaskStatusEnum.PENDING
                    task.completed_at = datetime.now(timezone.utc) if value else None
                    continue

                setattr(task, field, value)

            self.db.commit()
            self.db.refresh(task)

            # Create audit log entry
            new_data = task.to_dict()
            self._create_audit_entry(
                event_type="task.updated",
                task_id=task.id,
                event_data={"old": old_data, "new": new_data},
            )

            logger.info(f"Updated task: {task.id} - {task.title}")
            return TaskResponse.from_orm(task)

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating task {task_id}: {e}")
            raise HTTPException(status_code=500, detail="Error updating task")

    def delete_task(self, task_id: int) -> Dict[str, Any]:
        """Delete a task.

        Args:
            task_id: The task ID to delete

        Returns:
            Deletion confirmation

        Raises:
            HTTPException: If task not found
        """
        try:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            task_data = task.to_dict()
            self.db.delete(task)
            self.db.commit()

            # Create audit log entry
            self._create_audit_entry(
                event_type="task.deleted",
                task_id=task_id,
                event_data=task_data,
            )

            logger.info(f"Deleted task: {task_id}")
            return {"message": "Task deleted successfully", "id": task_id}

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting task {task_id}: {e}")
            raise HTTPException(status_code=500, detail="Error deleting task")

    # ========================================================================
    # Priority Operations (US3)
    # ========================================================================

    def update_priority(self, task_id: int, priority: str) -> TaskResponse:
        """Update task priority.

        Args:
            task_id: The task ID
            priority: New priority level (low/medium/high)

        Returns:
            TaskResponse with updated task

        Raises:
            HTTPException: If task not found or invalid priority
        """
        try:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            # Validate priority
            try:
                priority_enum = PriorityEnum(priority)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid priority. Must be one of: low, medium, high"
                )

            old_priority = task.priority.value if task.priority else None
            task.priority = priority_enum
            self.db.commit()
            self.db.refresh(task)

            # Create audit log entry
            self._create_audit_entry(
                event_type="task.updated",
                task_id=task.id,
                event_data={
                    "field": "priority",
                    "old_value": old_priority,
                    "new_value": priority,
                },
            )

            logger.info(f"Updated task {task_id} priority: {old_priority} -> {priority}")
            return TaskResponse.from_orm(task)

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating priority for task {task_id}: {e}")
            raise HTTPException(status_code=500, detail="Error updating priority")

    # ========================================================================
    # Tag Operations (US3)
    # ========================================================================

    def add_tags(self, task_id: int, tags: List[str]) -> TaskResponse:
        """Add tags to a task (additive - preserves existing tags).

        Args:
            task_id: The task ID
            tags: Tags to add

        Returns:
            TaskResponse with updated task

        Raises:
            HTTPException: If task not found
        """
        try:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            # Validate and format new tags
            new_tags = set()
            for tag in tags:
                if not tag.startswith('#'):
                    tag = f'#{tag}'
                if len(tag) > 50:
                    continue  # Skip invalid tags
                new_tags.add(tag)

            # Merge with existing tags
            existing_tags = set(task.tags or [])
            combined_tags = existing_tags.union(new_tags)

            # Limit to 10 tags
            combined_tags = list(combined_tags)[:10]

            old_tags = task.tags or []
            task.tags = combined_tags
            self.db.commit()
            self.db.refresh(task)

            # Create audit log entry
            self._create_audit_entry(
                event_type="task.updated",
                task_id=task.id,
                event_data={
                    "field": "tags",
                    "action": "add",
                    "old_tags": list(old_tags),
                    "new_tags": list(new_tags),
                },
            )

            logger.info(f"Added tags to task {task_id}: {list(new_tags)}")
            return TaskResponse.from_orm(task)

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding tags to task {task_id}: {e}")
            raise HTTPException(status_code=500, detail="Error adding tags")

    def remove_tags(self, task_id: int, tags: List[str]) -> TaskResponse:
        """Remove tags from a task.

        Args:
            task_id: The task ID
            tags: Tags to remove

        Returns:
            TaskResponse with updated task

        Raises:
            HTTPException: If task not found
        """
        try:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            # Normalize tags for comparison
            tags_to_remove = set()
            for tag in tags:
                if not tag.startswith('#'):
                    tag = f'#{tag}'
                tags_to_remove.add(tag)

            # Remove tags from existing
            existing_tags = set(task.tags or [])
            remaining_tags = existing_tags - tags_to_remove

            old_tags = task.tags or []
            task.tags = list(remaining_tags)
            self.db.commit()
            self.db.refresh(task)

            # Create audit log entry
            self._create_audit_entry(
                event_type="task.updated",
                task_id=task.id,
                event_data={
                    "field": "tags",
                    "action": "remove",
                    "old_tags": list(old_tags),
                    "removed_tags": list(tags_to_remove),
                },
            )

            logger.info(f"Removed tags from task {task_id}: {list(tags_to_remove)}")
            return TaskResponse.from_orm(task)

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing tags from task {task_id}: {e}")
            raise HTTPException(status_code=500, detail="Error removing tags")

    # ========================================================================
    # Recurrence Operations (US1)
    # ========================================================================

    async def complete_task(self, task_id: int, publish_event: bool = True) -> Dict[str, Any]:
        """Mark a task as completed and handle recurrence.

        For recurring tasks, automatically creates the next occurrence within 5 seconds.
        Optionally publishes task.completed event to Kafka via Dapr Pub/Sub.

        Args:
            task_id: The task ID to complete
            publish_event: Whether to publish task.completed event to Kafka

        Returns:
            Dict with updated task and next occurrence info (if recurring)
        """
        try:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            if task.status == TaskStatusEnum.COMPLETED:
                return {
                    "success": False,
                    "error": "Task is already completed",
                    "task": TaskResponse.from_orm(task).model_dump(),
                }

            # Store original task data for event publication
            original_task_data = task.to_dict()

            old_status = task.status
            is_recurring = task.recurrence not in (None, RecurrenceEnum.NONE)

            # Mark task as completed
            task.status = TaskStatusEnum.COMPLETED
            task.completed_at = datetime.now(timezone.utc)

            # Handle recurrence - create next occurrence
            next_occurrence = None
            if is_recurring:
                # Calculate next due date
                next_due_date = RecurrenceCalculator.calculate_next_due_date(
                    task.due_date or datetime.now(timezone.utc),
                    task.recurrence,
                )

                # Create next occurrence task
                next_task = Task(
                    title=task.title,
                    description=task.description,
                    priority=task.priority,
                    due_date=next_due_date if next_due_date else None,
                    tags=task.tags.copy() if task.tags else [],
                    recurrence=task.recurrence,
                    parent_task_id=task.id,
                    created_at=datetime.now(timezone.utc),
                )

                self.db.add(next_task)
                self.db.commit()
                self.db.refresh(next_task)

                next_occurrence = {
                    "id": next_task.id,
                    "title": next_task.title,
                    "due_date": str(next_task.due_date) if next_task.due_date else None,
                    "created_at": next_task.created_at.isoformat() if next_task.created_at else None,
                    "parent_task_id": task.id,
                }

                logger.info(
                    f"Completed recurring task: {task.id} - {task.title}, "
                    f"created next occurrence: {next_task.id} (due: {next_task.due_date})"
                )
            else:
                self.db.commit()
                logger.info(f"Completed task: {task.id}")

            self.db.refresh(task)

            # Create audit log entry
            self._create_audit_entry(
                event_type="task.completed",
                task_id=task.id,
                event_data={
                    "old_status": old_status.value if old_status else None,
                    "new_status": "completed",
                    "is_recurring": is_recurring,
                    "recurrence": task.recurrence.value if task.recurrence else None,
                },
            )

            # Publish event to Kafka if requested
            event_published = False
            if publish_event:
                event_published = await self._publish_task_completed_event(
                    task=task,
                    original_data=original_task_data,
                    is_recurring=is_recurring,
                )

            logger.info(f"Completed task: {task.id}")
            return {
                "success": True,
                "task": TaskResponse.from_orm(task).model_dump(),
                "is_recurring": is_recurring,
                "next_occurrence": next_occurrence,
                "event_published": event_published,
            }

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error completing task {task_id}: {e}")
            raise HTTPException(status_code=500, detail="Error completing task")

    async def _publish_task_completed_event(
        self,
        task: Task,
        original_data: Dict[str, Any],
        is_recurring: bool,
    ) -> bool:
        """Publish task.completed event to Kafka via Dapr Pub/Sub.

        Args:
            task: The completed task
            original_data: Original task data before completion
            is_recurring: Whether this is a recurring task
            next_occurrence_id: ID of the next occurrence (if recurring)

        Returns:
            True if event was published successfully
        """
        try:
            from services.event_publisher import get_event_publisher

            publisher = get_event_publisher()

            # Build task data for event
            task_data = {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "priority": task.priority.value if task.priority else None,
                "due_date": str(task.due_date) if task.due_date else None,
                "tags": task.tags,
                "recurrence": task.recurrence.value if task.recurrence else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "is_recurring": is_recurring,
            }

            # Publish event
            success = await publisher.publish_task_completed(
                task_id=task.id,
                task_data=task_data,
                is_recurring=is_recurring,
            )

            if success:
                logger.info(f"Published task.completed event for task {task.id}")
            else:
                logger.warning(f"Failed to publish task.completed event for task {task.id}")

            return success

        except Exception as e:
            logger.error(f"Error publishing task.completed event: {e}")
            return False

    def get_recurring_chain(self, task_id: int) -> List[Dict[str, Any]]:
        """Get the parent-child chain for a recurring task.

        Args:
            task_id: The task ID to get chain for

        Returns:
            List of tasks in the chain
        """
        try:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            # Find the root task (oldest in the chain)
            root_task = task
            while root_task.parent_task_id:
                root_task = self.db.query(Task).filter(
                    Task.id == root_task.parent_task_id
                ).first()
                if not root_task:
                    break

            # Get all tasks in the chain
            chain = []
            current = root_task
            while current:
                chain.append({
                    "id": current.id,
                    "title": current.title,
                    "due_date": current.due_date.isoformat() if current.due_date else None,
                    "status": current.status.value if current.status else None,
                    "created_at": current.created_at.isoformat() if current.created_at else None,
                    "parent_task_id": current.parent_task_id,
                })
                # Find next occurrence
                current = self.db.query(Task).filter(
                    Task.parent_task_id == current.id
                ).first()

            return chain

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting recurring chain for task {task_id}: {e}")
            raise HTTPException(status_code=500, detail="Error getting recurring chain")

    # ========================================================================
    # Search Operations (US4)
    # ========================================================================

    def search_tasks(self, search_request: TaskSearchRequest) -> TaskSearchResponse:
        """Advanced task search with filters and sorting.

        Args:
            search_request: Search parameters

        Returns:
            TaskSearchResponse with results
        """
        try:
            query = self.db.query(Task)

            # Apply text search if query provided
            if search_request.query:
                search_term = f"%{search_request.query}%"
                query = query.filter(
                    or_(
                        Task.title.ilike(search_term),
                        Task.description.ilike(search_term),
                    )
                )

            # Apply filters
            filters = search_request.filters
            if filters:
                if filters.status:
                    query = query.filter(Task.status == TaskStatusEnum(filters.status.value))

                if filters.priority:
                    query = query.filter(Task.priority == PriorityEnum(filters.priority.value))

                if filters.tags:
                    query = query.filter(Task.tags.contains(filters.tags))

                if filters.due_before:
                    query = query.filter(Task.due_date <= filters.due_before)

                if filters.due_after:
                    query = query.filter(Task.due_date >= filters.due_after)

                if filters.is_recurring is not None:
                    if filters.is_recurring:
                        query = query.filter(Task.recurrence != RecurrenceEnum.NONE)
                    else:
                        query = query.filter(Task.recurrence == RecurrenceEnum.NONE)

            # Get total count
            total_count = query.count()

            # Apply sorting
            sort_column = getattr(Task, search_request.sort_by.value, Task.created_at)

            if search_request.order == SortOrder.DESC:
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

            # Apply pagination
            tasks = query.offset(search_request.offset).limit(search_request.limit).all()

            # Convert to response format
            results = [TaskResponse.from_orm(task) for task in tasks]

            return TaskSearchResponse(
                results=results,
                total_count=total_count,
                query=search_request.query,
            )

        except Exception as e:
            logger.error(f"Error searching tasks: {e}")
            raise HTTPException(status_code=500, detail="Error searching tasks")

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _create_audit_entry(
        self,
        event_type: str,
        task_id: int,
        event_data: Dict[str, Any],
        parent_task_id: Optional[int] = None,
    ) -> None:
        """Create an audit log entry for an event.

        Args:
            event_type: Type of event (task.created, task.updated, etc.)
            task_id: Associated task ID
            event_data: Event payload
            parent_task_id: Parent task ID for recurring chains
        """
        try:
            audit_entry = AuditLogEntry(
                event_id=str(uuid4()),
                event_type=event_type,
                task_id=task_id,
                parent_task_id=parent_task_id,
                user_id=1,  # Single-user demo
                event_data=event_data,
            )
            self.db.add(audit_entry)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating audit entry: {e}")


# ========================================================================
# API Routes using TaskService
# ========================================================================

@router.get("/tasks", response_model=TaskListResponse)
async def get_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[str] = None,
    due_before: Optional[datetime] = None,
    due_after: Optional[datetime] = None,
    sort_by: str = "created_at",
    order: str = "desc",
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Get all tasks with optional filtering and sorting."""
    # Parse tags from comma-separated string
    tags_list = None
    if tags:
        tags_list = [t.strip() for t in tags.split(',')]

    service = TaskService(db)
    return service.get_tasks(
        status=status,
        priority=priority,
        tags=tags_list,
        due_before=due_before,
        due_after=due_after,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: Session = Depends(get_db)):
    """Get a specific task by ID."""
    service = TaskService(db)
    return service.get_task(task_id)


@router.post("/tasks", response_model=TaskResponse)
async def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task."""
    service = TaskService(db)
    return service.create_task(task)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
):
    """Update a task (partial update)."""
    service = TaskService(db)
    return service.update_task(task_id, task_update)


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task."""
    service = TaskService(db)
    return service.delete_task(task_id)


@router.put("/tasks/{task_id}/priority", response_model=TaskResponse)
async def update_task_priority(
    task_id: int,
    priority_update: UpdatePriorityRequest,
    db: Session = Depends(get_db),
):
    """Update task priority."""
    service = TaskService(db)
    return service.update_priority(task_id, priority_update.priority.value)


@router.post("/tasks/{task_id}/tags", response_model=TaskResponse)
async def add_task_tags(
    task_id: int,
    tags_request: AddTagsRequest,
    db: Session = Depends(get_db),
):
    """Add tags to a task."""
    service = TaskService(db)
    return service.add_tags(task_id, tags_request.tags)


@router.delete("/tasks/{task_id}/tags", response_model=TaskResponse)
async def remove_task_tags(
    task_id: int,
    tags_request: RemoveTagsRequest,
    db: Session = Depends(get_db),
):
    """Remove tags from a task."""
    service = TaskService(db)
    return service.remove_tags(task_id, tags_request.tags)


@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: int,
    publish_event: bool = True,
    db: Session = Depends(get_db),
):
    """Mark a task as completed.

    For recurring tasks, automatically creates the next occurrence.
    Publishes task.completed event to Kafka unless disabled.
    """
    service = TaskService(db)
    return await service.complete_task(task_id, publish_event=publish_event)


@router.get("/tasks/{task_id}/chain", response_model=List[Dict[str, Any]])
async def get_task_chain(task_id: int, db: Session = Depends(get_db)):
    """Get the parent-child chain for a recurring task."""
    service = TaskService(db)
    return service.get_recurring_chain(task_id)


@router.post("/tasks/search", response_model=TaskSearchResponse)
async def search_tasks(
    search_request: TaskSearchRequest,
    db: Session = Depends(get_db),
):
    """Advanced task search with filters and sorting."""
    service = TaskService(db)
    return service.search_tasks(search_request)


@router.post("/tasks/{task_id}/subtasks", response_model=SubtaskResponse)
async def create_subtask_for_task(
    task_id: int,
    subtask: SubtaskCreate,
    db: Session = Depends(get_db),
):
    """Create a new subtask for a specific parent task."""
    service = TaskService(db)
    return service.create_subtask(parent_task_id=task_id, subtask_data=subtask)


@router.post("/tasks/{task_id}/comments", response_model=CommentResponse)
async def create_comment_for_task(
    task_id: int,
    comment: CommentCreate,
    db: Session = Depends(get_db),
):
    """Create a new comment for a specific task."""
    service = TaskService(db)
    return service.create_comment_for_task(task_id=task_id, comment_data=comment)


@router.post("/tasks/{task_id}/attachments", response_model=AttachmentResponse)
async def create_attachment_for_task(
    task_id: int,
    attachment: AttachmentCreate,
    db: Session = Depends(get_db),
):
    """Create a new attachment for a specific task."""
    service = TaskService(db)
    return service.create_attachment_for_task(task_id=task_id, attachment_data=attachment)


@router.get("/projects/", response_model=List[ProjectResponse])
async def get_all_projects(db: Session = Depends(get_db)):
    """Retrieve all projects."""
    service = ProjectService(db)
    return service.get_projects()


@router.post("/projects/", response_model=ProjectResponse)
async def create_new_project(
    project: ProjectCreate, db: Session = Depends(get_db)
):
    """Create a new project."""
    service = ProjectService(db)
    return service.create_project(project)
