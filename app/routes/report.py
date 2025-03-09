# app/routers/report.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.task import Task  # adjust import paths as needed
from app.models.employee import Employee, RoleEnum
from app.models.attendance import AttendanceLog
from app.models.breaks import BreakLog
from app.models.attendance import LateRecord
from app.models.attendance import Penalty
from app.models.attendance import Bonus
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date, timedelta

router = APIRouter()

# --- Pydantic Response Schemas ---
class TaskOut(BaseModel):
    id: int
    description: str
    task_date: date
    status: bool
    completed_at: Optional[datetime]

    class Config:
        orm_mode = True

class BreakLogOut(BaseModel):
    id: int
    break_type: str
    break_start: datetime
    break_end: Optional[datetime]
    total_break_time: Optional[float]

    class Config:
        orm_mode = True

class LateRecordOut(BaseModel):
    id: int
    late_duration_minutes: float
    deduction_amount: float

    class Config:
        orm_mode = True

class PenaltyOut(BaseModel):
    id: int
    description: str
    price: float

    class Config:
        orm_mode = True

class BonusOut(BaseModel):
    id: int
    description: str
    price: float

    class Config:
        orm_mode = True

class AttendanceLogOut(BaseModel):
    id: int
    clock_in: datetime
    clock_out: Optional[datetime]
    total_hours: Optional[float]
    net_pay: Optional[float]
    break_logs: List[BreakLogOut]
    late_record: Optional[LateRecordOut]
    penalties: List[PenaltyOut]
    bonuses: List[BonusOut]

    class Config:
        orm_mode = True

class EmployeeReport(BaseModel):
    id: int
    name: str
    role: str
    hourly_wage: float
    tasks: List[TaskOut]
    attendance_logs: List[AttendanceLogOut]

    class Config:
        orm_mode = True

# --- API Endpoint ---
@router.get("/report/{employee_id}", response_model=EmployeeReport)
def get_employee_report(employee_id: int, db: Session = Depends(get_db)):
    # Calculate current week boundaries (Monday to Sunday)
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)  # Sunday

    # Convert dates to datetime for comparison with AttendanceLog.clock_in
    start_datetime = datetime.combine(start_of_week, datetime.min.time())
    end_datetime = datetime.combine(end_of_week, datetime.max.time())

    # Get the employee
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Get tasks for the employee for the current week
    tasks = (
        db.query(Task)
        .filter(
            Task.employee_id == employee_id,
            Task.task_date >= start_of_week,
            Task.task_date <= end_of_week,
        )
        .all()
    )

    # Get attendance logs for the employee for the current week
    attendance_logs = (
        db.query(AttendanceLog)
        .filter(
            AttendanceLog.employee_id == employee_id,
            AttendanceLog.clock_in >= start_datetime,
            AttendanceLog.clock_in <= end_datetime,
        )
        .all()
    )

    attendance_logs_out = []
    for log in attendance_logs:
        # Calculate net pay if clock_out is set
        net_pay = log.calculate_net_pay() if log.clock_out else None

        log_data = {
            "id": log.id,
            "clock_in": log.clock_in,
            "clock_out": log.clock_out,
            "total_hours": float(log.total_hours) if log.total_hours is not None else None,
            "net_pay": net_pay,
            "break_logs": [
                {
                    "id": b.id,
                    "break_type": b.break_type,
                    "break_start": b.break_start,
                    "break_end": b.break_end,
                    "total_break_time": float(b.total_break_time) if b.total_break_time is not None else None,
                }
                for b in log.break_logs
            ],
            "late_record": {
                "id": log.late_record.id,
                "late_duration_minutes": float(log.late_record.late_duration_minutes),
                "deduction_amount": float(log.late_record.deduction_amount),
            } if log.late_record else None,
            "penalties": [
                {"id": p.id, "description": p.description, "price": float(p.price)}
                for p in log.penalties
            ],
            "bonuses": [
                {"id": b.id, "description": b.description, "price": float(b.price)}
                for b in log.bonuses
            ],
        }
        attendance_logs_out.append(log_data)

    # Build the report data
    report = {
        "id": emp.id,
        "name": emp.name,
        "role": emp.role.value if isinstance(emp.role, RoleEnum) else emp.role,
        "hourly_wage": float(emp.hourly_wage),
        "tasks": tasks,
        "attendance_logs": attendance_logs_out,
    }
    return report
