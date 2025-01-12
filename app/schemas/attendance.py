from pydantic import BaseModel
from datetime import datetime
from typing import Optional

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
    created_at: datetime

    class Config:
        from_attributes = True