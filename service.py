from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
import logging

from database import get_db
from models import Task

logger = logging.getLogger("app")

router = APIRouter()

# Pydantic models for request/response validation
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[int] = 0
    tags: Optional[List[str]] = None
    due_date: Optional[date] = None
    recurrence_pattern: Optional[str] = None
    reminder_time: Optional[datetime] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[int] = None
    tags: Optional[List[str]] = None
    due_date: Optional[date] = None
    recurrence_pattern: Optional[str] = None
    reminder_time: Optional[datetime] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    completed: bool
    created_at: datetime
    priority: int
    tags: Optional[List[str]]
    due_date: Optional[date]
    recurrence_pattern: Optional[str]
    next_recurrence_date: Optional[date]
    recurrence_start_date: Optional[date]
    recurrence_end_date: Optional[date]
    reminder_time: Optional[datetime]

    class Config:
        from_attributes = True

# API Routes
@router.get("/tasks/", response_model=List[TaskResponse])
async def get_tasks(
    completed: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get all tasks, optionally filtered by completion status."""
    try:
        query = db.query(Task)
        
        if completed is not None:
            query = query.filter(Task.completed == completed)
        
        tasks = query.order_by(Task.created_at.desc()).all()
        logger.info(f"Retrieved {len(tasks)} tasks")
        return tasks
    except Exception as e:
        logger.error(f"Error retrieving tasks: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving tasks")

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: Session = Depends(get_db)):
    """Get a specific task by ID."""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving task")

@router.post("/tasks/", response_model=TaskResponse)
async def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task."""
    try:
        db_task = Task(
            title=task.title,
            description=task.description,
            priority=task.priority or 0,
            tags=task.tags,
            due_date=task.due_date,
            recurrence_pattern=task.recurrence_pattern,
            reminder_time=task.reminder_time
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        logger.info(f"Created task: {db_task.id} - {db_task.title}")
        return db_task
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail="Error creating task")

@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int, 
    task_update: TaskUpdate, 
    db: Session = Depends(get_db)
):
    """Update a task (partial update)."""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Update only the fields that were provided
        update_data = task_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)
        
        db.commit()
        db.refresh(task)
        logger.info(f"Updated task: {task.id} - {task.title}")
        return task
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Error updating task")

@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def replace_task(
    task_id: int, 
    task_update: TaskUpdate, 
    db: Session = Depends(get_db)
):
    """Replace a task (full update)."""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Update fields
        update_data = task_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)
        
        db.commit()
        db.refresh(task)
        logger.info(f"Replaced task: {task.id} - {task.title}")
        return task
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error replacing task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Error replacing task")

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task."""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        db.delete(task)
        db.commit()
        logger.info(f"Deleted task: {task_id}")
        return {"message": "Task deleted successfully", "id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Error deleting task")

@router.post("/tasks/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: int, db: Session = Depends(get_db)):
    """Mark a task as completed."""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task.completed = True
        db.commit()
        db.refresh(task)
        logger.info(f"Completed task: {task.id}")
        return task
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error completing task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Error completing task")

@router.post("/tasks/{task_id}/uncomplete", response_model=TaskResponse)
async def uncomplete_task(task_id: int, db: Session = Depends(get_db)):
    """Mark a task as not completed."""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task.completed = False
        db.commit()
        db.refresh(task)
        logger.info(f"Uncompleted task: {task.id}")
        return task
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error uncompleting task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Error uncompleting task")