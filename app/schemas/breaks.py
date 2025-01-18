from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class BreakClockIn(BaseModel):
    attendance_id: int
    break_type: str

    class Config:
        from_attributes = True

class BreakClockOut(BaseModel):
    attendance_id: int

    class Config:
        from_attributes = True

class BreakLogBase(BaseModel):
    attendance_id: int
    break_type: str
    break_start: Optional[datetime] = None
    break_end: Optional[datetime] = None
    total_break_time: Optional[float] = None

    class Config:
        from_attributes = True


class BreakLogCreate(BreakLogBase):
    pass


class BreakLogUpdate(BaseModel):
    break_end: datetime
    total_break_time: float


class BreakLogResponse(BreakLogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # Enable ORM integration

class UpdateBreaksRequest(BaseModel):
    break_logs: List[BreakLogBase]


class CreateNewBreak(BaseModel):
    attendance_id: int
    break_type: str
    break_start: str
    break_end: str

    class Config:
        from_attributes = True