from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


# Enum for role
class RoleEnum(str, Enum):
    admin = "admin"
    employee = "employee"


class EmployeeCreate(BaseModel):
    name: str
    role: RoleEnum
    hourly_wage: float

    class Config:
        from_attributes = True


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    hourly_wage: Optional[float] = None

    class Config:
        from_attributes = True

class EmployeeLogin(BaseModel):
    qr_id: str

    class Config:
        from_attributes = True

class EmployeeResponse(EmployeeCreate):
    id: int
    qr_id: str
    created_at: datetime

    class Config:
        from_attributes = True
