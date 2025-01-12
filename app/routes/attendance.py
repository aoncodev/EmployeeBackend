from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.attendance import AttendanceLog
from app.models.employee import Employee
from app.schemas.attendance import Attendance
from datetime import datetime, date
from app.models.breaks import BreakLog

router = APIRouter()

@router.get("/attendance", response_model=List[Attendance])
def get_employee_attendance(db: Session = Depends(get_db)):
    db_attendance = db.query(AttendanceLog).all()

    if not db_attendance:
        raise HTTPException(status_code=404, detail="Attendance not found")
    return db_attendance


@router.get("/attendance/{employee_id}", response_model=List[Attendance])
def get_employee_by_id(employee_id:int, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    db_attendance = db.query(AttendanceLog).filter(AttendanceLog.employee_id == employee_id).all()

    if not db_attendance:
        raise HTTPException(status_code=404, detail=f"Attendance for employee {employee.name} not found")
    
    return db_attendance

@router.post("/clock-in/")
def clock_in(employee_id: int, db: Session = Depends(get_db)):
    try:
        # Check if the employee exists
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")

        # Check if employee already clocked in today
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())
        
        existing_clock_in = (
            db.query(AttendanceLog)
            .filter(
                AttendanceLog.employee_id == employee_id,
                AttendanceLog.clock_in >= today_start,
                AttendanceLog.clock_in <= today_end
            )
            .first()
        )

        if existing_clock_in:
            raise HTTPException(status_code=400, detail="Employee has already clocked in for today")

        # Create a new clock-in record
        new_attendance = AttendanceLog(
            employee_id=employee_id,
            clock_in=datetime.now()
        )
        db.add(new_attendance)
        db.commit()
        db.refresh(new_attendance)

        return {"message": "Clock-in successful", "data": new_attendance}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@router.post("/clock-out/")
def clock_out(employee_id: int, db: Session = Depends(get_db)):
    """
    Clock out an employee and finalize attendance and break records for today.
    """
    try:
        # Check if the employee exists
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")

        # Check if the employee has a valid clock-in record for today
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())

        attendance_record = (
            db.query(AttendanceLog)
            .filter(
                AttendanceLog.employee_id == employee_id,
                AttendanceLog.clock_in >= today_start,
                AttendanceLog.clock_in <= today_end,
                AttendanceLog.clock_out == None  # Ensure clock_out has not already occurred
            )
            .first()
        )

        if not attendance_record:
            raise HTTPException(
                status_code=400, 
                detail="No valid clock-in record found for today or employee has already clocked out"
            )

        # Check for an ongoing break and close it if found
        ongoing_break = (
            db.query(BreakLog)
            .filter(
                BreakLog.attendance_id == attendance_record.id,
                BreakLog.break_end == None  # Break is still ongoing
            )
            .order_by(BreakLog.break_start.desc())  # Ensure we get the last break
            .first()
        )

        if ongoing_break:
            ongoing_break.break_end = datetime.now()
            ongoing_break.total_break_time = round(
                (ongoing_break.break_end - ongoing_break.break_start).total_seconds() / 60.0, 2
            )

        # Finalize the attendance record with clock-out
        clock_out_time = datetime.now()
        total_hours = (clock_out_time - attendance_record.clock_in).total_seconds() / 3600

        attendance_record.clock_out = clock_out_time
        attendance_record.total_hours = round(total_hours, 2)

        # Commit the changes to the database
        db.commit()
        db.refresh(attendance_record)

        return {"message": "Clock-out successful", "data": {
            "attendance": attendance_record,
            "last_break": ongoing_break
        }}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    