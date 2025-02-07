from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.attendance import AttendanceLog
from app.models.employee import Employee
from app.schemas.attendance import Attendance, ClockOutRequest, ClockInRequest
from app.schemas.breaks import UpdateBreaksRequest
from datetime import datetime, date
from app.models.breaks import BreakLog
from sqlalchemy.orm import joinedload
import logging
import pytz  # For timezone conversion
from sqlalchemy import extract
import math
from math import ceil
from datetime import datetime, date, timedelta


logger = logging.getLogger('uvicorn.error')


router = APIRouter()

@router.get("/attendance", response_model=List[Attendance])
def get_employee_attendance(db: Session = Depends(get_db)):
    db_attendance = db.query(AttendanceLog).all()

    if not db_attendance:
        raise HTTPException(status_code=404, detail="Attendance not found")
    return db_attendance


@router.get("/get/attendance/{attendance_id}")
def get_attendance_by_id(attendance_id: int, db: Session = Depends(get_db)):
    """
    Fetch attendance record by ID and calculate related details.
    Assumes all datetime values in the database are in KST.
    """
    # Fetch the attendance record by ID
    attendance = db.query(AttendanceLog).options(
        joinedload(AttendanceLog.break_logs)  # Eager load associated break_logs
    ).filter(AttendanceLog.id == attendance_id).first()

    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    # Initialize totals
    total_work_hours = 0
    total_break_time = 0
    total_hours_excluding_breaks = 0
    total_wage = 0

    # Calculate totals if clock_in is available
    if attendance.clock_in:
        clock_in = attendance.clock_in
        clock_out = attendance.clock_out or datetime.now()  # Use current time if clock_out is missing

        # Calculate total work hours
        total_work_hours = (clock_out - clock_in).total_seconds() / 3600  # Convert seconds to hours

        # Calculate total break time
        total_break_time = sum(
            (
                (br.break_end - br.break_start).total_seconds() / 3600
                for br in attendance.break_logs
                if br.break_start and br.break_end
            ),
            0
        )

        # Calculate total hours excluding breaks
        total_hours_excluding_breaks = max(0, total_work_hours - total_break_time)

        # Calculate total wage
        hourly_wage = float(attendance.employee.hourly_wage) if attendance.employee and attendance.employee.hourly_wage else 0
        total_wage = total_hours_excluding_breaks * hourly_wage

    # Calculate total break count
    total_breaks = len([br for br in attendance.break_logs if br.break_start and br.break_end])

    # Prepare the response
    result = {
        "id": attendance.id,
        "employee_name": attendance.employee.name if attendance.employee else "Unknown",
        "clock_in": attendance.clock_in,
        "clock_out": attendance.clock_out,
        "has_clocked_out": attendance.clock_out is not None,
        "total_hours": round(total_work_hours, 2),
        "total_hours_excluding_breaks": round(total_hours_excluding_breaks, 2),
        "total_wage": round(total_wage, 2),
        "total_break_time": round(total_break_time, 2),  # Total break time in hours
        "total_breaks": total_breaks,  # Count of completed breaks
        "break_logs": [
            {
                "id": br.id,
                "break_type": br.break_type,
                "break_start": br.break_start,
                "break_end": br.break_end,
                "total_break_time": round(
                    (br.break_end - br.break_start).total_seconds() / 3600, 2
                ) if br.break_start and br.break_end else None,
            }
            for br in attendance.break_logs
        ],
    }

    return result


@router.get("/attendance/{employee_id}")
def get_employee_by_id(
    employee_id: int,
    month: str = "all",  # Default to "all" for no month filter
    page: int = 1,  # Default to the first page
    per_page: int = 10,  # Default to 10 records per page
    db: Session = Depends(get_db),
):
    """
    Get attendance records for an employee, filtered by month if specified.
    Assumes all timestamps are stored in KST.
    """
    # Fetch the employee record
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Query attendance logs, including related break logs
    query = db.query(AttendanceLog).options(
        joinedload(AttendanceLog.break_logs)
    ).filter(
        AttendanceLog.employee_id == employee_id
    )

    # Apply month filter if specified
    if month != "all":
        try:
            month_int = int(month)
            if 1 <= month_int <= 12:  # Ensure valid month range
                query = query.filter(extract("month", AttendanceLog.clock_in) == month_int)
            else:
                raise ValueError
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid month parameter")

    # Sort by clock_in (newest first)
    query = query.order_by(AttendanceLog.clock_in.desc())

    # Get total record count for pagination
    total_records = query.count()

    # Apply pagination
    query = query.offset((page - 1) * per_page).limit(per_page)

    # Fetch attendance records
    db_attendance = query.all()

    if not db_attendance:
        raise HTTPException(
            status_code=404, detail=f"Attendance for employee {employee.name} not found"
        )

    # Prepare response
    attendance_records = []
    for attendance in db_attendance:
        # Initialize totals
        total_work_hours = 0
        total_break_hours = 0
        total_hours_excluding_breaks = 0
        total_wage = 0
        hourly_wage = float(employee.hourly_wage) if employee.hourly_wage else 0

        # Calculate total work hours and break hours if clock_in is available
        if attendance.clock_in:
            clock_in = attendance.clock_in
            clock_out = attendance.clock_out or datetime.now()  # Use current time if clock_out is missing

            # Calculate total work hours
            total_work_hours = (clock_out - clock_in).total_seconds() / 3600

            # Calculate total break hours
            total_break_hours = sum(
                (
                    (br.break_end - br.break_start).total_seconds() / 3600
                    if br.break_start and br.break_end
                    else 0
                )
                for br in attendance.break_logs
            )

            # Calculate total hours excluding breaks
            total_hours_excluding_breaks = max(0, total_work_hours - total_break_hours)

            # Calculate total wage
            total_wage = total_hours_excluding_breaks * hourly_wage

        # Append the attendance record to the result
        attendance_records.append({
            "id": attendance.id,
            "employee_name": employee.name,
            "clock_in": attendance.clock_in,
            "clock_out": attendance.clock_out,
            "has_clocked_out": attendance.clock_out is not None,
            "total_hours": round(total_work_hours, 2),
            "total_hours_excluding_breaks": round(total_hours_excluding_breaks, 2),
            "total_break_hours": round(total_break_hours, 2),
            "total_wage": round(total_wage, 2),
            "break_logs": [
                {
                    "id": br.id,
                    "break_type": br.break_type,
                    "break_start": br.break_start,
                    "break_end": br.break_end,
                    "total_break_time": round(
                        (br.break_end - br.break_start).total_seconds() / 3600, 2
                    ) if br.break_start and br.break_end else None,
                }
                for br in attendance.break_logs
            ],
        })

    total_pages = ceil(total_records / per_page)

    return {
        "attendance_records": attendance_records,
        "total_pages": total_pages,
        "current_page": page,
        "records_per_page": per_page,
        "total_records": total_records,
    }





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

        # Define the boundaries for today
        today = date.today()
        start_of_today = datetime.combine(today, datetime.min.time())
        start_of_tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())

        # Find an open attendance record (clock_out is None)
        # that started before tomorrow, so that it catches records that started yesterday as well.
        attendance_record = (
            db.query(AttendanceLog)
            .filter(
                AttendanceLog.employee_id == employee_id,
                AttendanceLog.clock_in < start_of_tomorrow,  # clock in happened before tomorrow
                AttendanceLog.clock_out == None              # still ongoing
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
            .order_by(BreakLog.break_start.desc())  # Get the most recent break
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

    

@router.put("/attendance/edit/clock_in")
def update_clock_in(request: ClockInRequest, db: Session = Depends(get_db)):
    """
    Updates the clock-in time for an attendance record. 
    Assumes all timestamps are in KST.
    """
    try:
        # Fetch the attendance record by ID
        attendance = db.query(AttendanceLog).filter(AttendanceLog.id == request.attendance_id).first()

        if not attendance:
            raise HTTPException(status_code=404, detail="Attendance record not found")

        # If clock_in is provided in the request, convert the string to a datetime object
        if request.clock_in:
            try:
                # Parse clock_in as KST datetime
                kst_time = datetime.fromisoformat(request.clock_in)  # Input should already be KST formatted
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid datetime format for clock_in")

            # Update the clock_in field in the database
            attendance.clock_in = kst_time

            # Recalculate and update total hours if clock_out is set
            attendance.update_total_hours(db)

        db.commit()
        db.refresh(attendance)

        return {
            "message": "Clock-in time updated successfully",
            "data": {
                "id": attendance.id,
                "employee_id": attendance.employee_id,
                "clock_in": attendance.clock_in,
                "total_hours": attendance.total_hours,
            },
        }

    except HTTPException as e:
        raise e  # Re-raise known HTTP exceptions
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



@router.put("/attendance/edit/clock_out")
def update_clock_out(request: ClockOutRequest, db: Session = Depends(get_db)):
    """
    Updates the clock-out time for an attendance record.
    Assumes all timestamps are in KST.
    """
    try:
        # Fetch the attendance record by ID
        attendance = db.query(AttendanceLog).filter(AttendanceLog.id == request.attendance_id).first()

        if not attendance:
            raise HTTPException(status_code=404, detail="Attendance record not found")

        # If clock_out is provided in the request, convert the string to a datetime object
        if request.clock_out:
            try:
                # Parse clock_out as KST datetime
                kst_time = datetime.fromisoformat(request.clock_out)  # Input should already be KST formatted
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid datetime format for clock_out")

            # Update the clock_out field in the database
            attendance.clock_out = kst_time

            # Recalculate and update total hours after clock_out is set
            attendance.update_total_hours(db)

        db.commit()
        db.refresh(attendance)

        return {
            "message": "Clock-out time updated successfully",
            "data": {
                "id": attendance.id,
                "employee_id": attendance.employee_id,
                "clock_out": attendance.clock_out,
                "total_hours": attendance.total_hours,
            },
        }

    except HTTPException as e:
        raise e  # Re-raise known HTTP exceptions
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

    

@router.delete("/attendance/delete/{attendance_id}/clock_out")
def delete_clock_out(attendance_id: int, db: Session = Depends(get_db)):
    try:
        # Fetch the attendance record by ID
        attendance = db.query(AttendanceLog).filter(AttendanceLog.id == attendance_id).first()

        if not attendance:
            raise HTTPException(status_code=404, detail="Attendance record not found")

        # If clock_out is provided in the request, convert the string to a datetime object
    

        attendance.clock_out = None

        # Calculate and update the total hours after clock_out is set
        attendance.total_hours = 0

        db.commit()
        db.refresh(attendance)

        return {"message": "Clock-out time deleted successfully", "data": {
            "id": attendance.id,
            "employee_id": attendance.employee_id,
            "clock_out": attendance.clock_out,
            "total_hours": attendance.total_hours
        }}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


