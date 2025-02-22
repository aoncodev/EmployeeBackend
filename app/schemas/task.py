# app/schemas/task.py
from datetime import date, datetime
from pydantic import BaseModel
from typing import Optional

class TaskBase(BaseModel):
    description: str
    employee_id: int
    task_date: date
    status: bool = False

class TaskCreate(TaskBase):
    completed_at: Optional[datetime] = None

class TaskOut(TaskBase):
    id: int
    completed_at: Optional[datetime]

    class Config:
        orm_mode = True
