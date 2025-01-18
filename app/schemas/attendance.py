from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.schemas.breaks import BreakLogBase

class AttendanceBase(BaseModel):
    employee_id: int
    clock_in: Optional[datetime] = None
    clock_out: Optional[datetime] = None
    total_hours: Optional[float] = None

    class Config:
        from_attribures = True


class AttendanceCreate(AttendanceBase):
    pass

class AttendanceUpdate(BaseModel):
    clock_out: Optional[datetime] = None
    total_hours: Optional[float] = None


class Attendance(AttendanceBase):
    id: int
    employee_name: str
    total_hours_excluding_breaks: Optional[float]
    total_wage: float  # New field
    break_logs: List[BreakLogBase]  # Nested break logs
    created_at: datetime

    class Config:
        from_attributes = True


class ClockOutRequest(BaseModel):
    attendance_id: int
    clock_out: Optional[str] = None 

class ClockInRequest(BaseModel):
    attendance_id: int
    clock_in: str  # Expecting ISO 8601 formatted string

    
