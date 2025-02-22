from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from app.database import get_db
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskOut

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)

@router.get("/filter", response_model=List[TaskOut])
def get_tasks_filtered(
    employee_id: Optional[int] = Query(None, description="Filter tasks by employee id"),
    task_date: Optional[str] = Query(None, description="Filter tasks by date in YYYY-MM-DD format"),
    db: Session = Depends(get_db)
):
    """
    Get tasks filtered by employee_id and/or task_date.
    - **employee_id**: (Optional) ID of the employee.
    - **task_date**: (Optional) Date of the task in YYYY-MM-DD format.
    """
    query = db.query(Task)
    
    if employee_id is not None:
        query = query.filter(Task.employee_id == employee_id)
    
    if task_date is not None:
        try:
            # Parse the date string into a date object
            parsed_date = datetime.strptime(task_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD."
            )
        query = query.filter(Task.task_date == parsed_date)
    
    tasks = query.all()
    return tasks

@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """
    Create a new task.
    Expected JSON body:
    {
      "description": "Task description",
      "employee_id": 1,
      "task_date": "2025-02-20",
      "status": false,
      "completed_at": null
    }
    """
    new_task = Task(
        description=task.description,
        employee_id=task.employee_id,
        task_date=task.task_date,
        status=task.status,
        completed_at=task.completed_at
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@router.get("/", response_model=List[TaskOut])
def get_tasks(db: Session = Depends(get_db)):
    """
    Get all tasks.
    """
    tasks = db.query(Task).all()
    return tasks

@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """
    Get a single task by its ID.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.put("/{task_id}/toggle", response_model=TaskOut)
def toggle_task_status(task_id: int, db: Session = Depends(get_db)):
    """
    Toggle the status of a task.
    This endpoint reverses the task status.
    If the task is toggled to True, it sets the completed_at field to the current time.
    If toggled to False, it clears the completed_at field.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Toggle the status
    task.status = not task.status
    
    # Update completed_at accordingly
    if task.status:
        task.completed_at = datetime.now()
    else:
        task.completed_at = None

    db.commit()
    db.refresh(task)
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """
    Delete a task by its ID.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return


