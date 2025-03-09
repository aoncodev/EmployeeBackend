# app/routers/report.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.task import Task  # adjust import paths as needed
from app.models.employee import Employee, RoleEnum
from app.models.attendance import AttendanceLog, LateRecord, Penalty, Bonus
from app.models.breaks import BreakLog
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

@router.get("/report/{employee_id}", response_model=EmployeeReport)
def get_employee_report(
    employee_id: int,
    start_date: Optional[str] = Query(None, description="Week start date in YYYY-MM-DD format"),
    db: Session = Depends(get_db)
):
    """
    Generate a simplified report for the given employee for a one-week time frame.
    If 'start_date' is provided, it is used as the Monday of that week.
    Otherwise, the current week's Monday is used.
    """
    # Determine the start of the week
    if start_date:
        try:
            start_of_week = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    else:
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # Convert dates to naive datetimes for filtering
    start_datetime = datetime.combine(start_of_week, datetime.min.time())
    end_datetime = datetime.combine(end_of_week, datetime.max.time())

    # Get the employee
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Get tasks for the employee for the week
    tasks = (
        db.query(Task)
        .filter(
            Task.employee_id == employee_id,
            Task.task_date >= start_of_week,
            Task.task_date <= end_of_week,
        )
        .all()
    )

    # Get attendance logs for the employee for the week
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
        # Calculate work hours and wages if clock_in exists
        if log.clock_in:
            clock_in = log.clock_in
            clock_out = log.clock_out or datetime.now()  # use current time if clock_out is missing
            total_work_hours = (clock_out - clock_in).total_seconds() / 3600
            total_break_time = sum(
                (br.break_end - br.break_start).total_seconds() / 3600
                for br in log.break_logs
                if br.break_start and br.break_end
            )
            effective_hours = max(0, total_work_hours - total_break_time)
            hourly_wage = float(emp.hourly_wage) if emp.hourly_wage else 0
            total_wage = effective_hours * hourly_wage
        else:
            total_work_hours = 0
            total_break_time = 0
            effective_hours = 0
            total_wage = 0

        late_deduction = float(log.late_record.deduction_amount) if log.late_record else 0
        total_penalties = sum(float(p.price) for p in log.penalties) if log.penalties else 0
        total_bonuses = sum(float(b.price) for b in log.bonuses) if log.bonuses else 0

        net_pay = (total_wage - (late_deduction + total_penalties)) + total_bonuses

        log_data = {
            "id": log.id,
            "clock_in": log.clock_in,
            "clock_out": log.clock_out,
            "net_pay": round(net_pay, 0),  # rounded to 0 decimals (KRW)
            "break_logs": [
                {
                    "id": br.id,
                    "break_type": br.break_type,
                    "break_start": br.break_start,
                    "break_end": br.break_end,
                    "total_break_time": round(
                        ((br.break_end - br.break_start).total_seconds() / 3600), 2
                    ) if br.break_start and br.break_end else None,
                }
                for br in log.break_logs
            ],
            "late_record": {
                "id": log.late_record.id,
                "late_duration_minutes": int(round(float(log.late_record.late_duration_minutes))),
                "deduction_amount": round(float(log.late_record.deduction_amount), 0),
            } if log.late_record else None,
            "penalties": [
                {
                    "id": p.id,
                    "description": p.description,
                    "price": round(float(p.price), 0),
                }
                for p in log.penalties
            ],
            "bonuses": [
                {
                    "id": b.id,
                    "description": b.description,
                    "price": round(float(b.price), 0),
                }
                for b in log.bonuses
            ],
        }
        attendance_logs_out.append(log_data)

    report = {
        "id": emp.id,
        "name": emp.name,
        "role": emp.role.value if hasattr(emp.role, "value") else emp.role,
        "hourly_wage": round(float(emp.hourly_wage), 0),
        "tasks": [
            {
                "id": t.id,
                "description": t.description,
                "task_date": t.task_date,
                "status": t.status,
                "completed_at": t.completed_at,
            }
            for t in tasks
        ],
        "attendance_logs": attendance_logs_out,
    }
    return report
