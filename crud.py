import logging
from sqlalchemy.orm import Session
import models, schemas

logger = logging.getLogger("app")

def get_task(db: Session, task_id: int):
    return db.query(models.Task).filter(models.Task.id == task_id).first()

def get_tasks(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Task).offset(skip).limit(limit).all()

def create_task(db: Session, task: schemas.TaskCreate):
    try:
        db_task = models.Task(**task.dict())
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        return db_task
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        db.rollback()
        raise e

def update_task(db: Session, task_id: int, task: schemas.TaskUpdate):
    db_task = get_task(db, task_id)
    if db_task:
        try:
            update_data = task.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_task, key, value)
            db.commit()
            db.refresh(db_task)
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            db.rollback()
            raise e
    return db_task

def delete_task(db: Session, task_id: int):
    db_task = get_task(db, task_id)
    if db_task:
        try:
            db.delete(db_task)
            db.commit()
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            db.rollback()
            raise e
    return db_task
