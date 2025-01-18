from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.attendance import AttendanceLog
from app.models.employee import Employee
from app.models.breaks import BreakLog
from app.schemas.breaks import BreakLogBase, BreakLogResponse, BreakClockIn, BreakClockOut, CreateNewBreak
from datetime import datetime, date
from typing import Optional
import pytz

router = APIRouter()



@router.get("/breaks/", response_model=List[BreakLogResponse])
def get_breaks(
    break_start: Optional[datetime] = Query(None, description="Filter by break start date/time"),
    break_end: Optional[datetime] = Query(None, description="Filter by break end date/time"),
    db: Session = Depends(get_db)
):
    """
    Get a list of all break logs. Optionally filter by break_start and break_end.
    """
    try:
        query = db.query(BreakLog)
        
        # Filter by break_start if provided
        if break_start:
            query = query.filter(BreakLog.break_start >= break_start)
        
        # Filter by break_end if provided
        if break_end:
            query = query.filter(BreakLog.break_end <= break_end)

        # Execute the query and retrieve results
        break_logs = query.all()
        return break_logs

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@router.post("/breaks/start/", response_model=BreakLogResponse)
def break_start(break_data: BreakClockIn, db: Session = Depends(get_db)):
    """
    Start a break for an employee's attendance log.
    """
    try:
        # Check if an ongoing break exists for the given attendance_id
        ongoing_break = (
            db.query(BreakLog)
            .filter(BreakLog.attendance_id == break_data.attendance_id, BreakLog.break_end == None)
            .first()
        )
        if ongoing_break:
            raise HTTPException(status_code=400, detail="An ongoing break already exists for this attendance log.")
        
        # Create a new break log
        new_break = BreakLog(
            attendance_id=break_data.attendance_id,
            break_type=break_data.break_type,
            break_start=datetime.now()
        )
        db.add(new_break)
        db.commit()
        db.refresh(new_break)

        return new_break

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")




@router.post("/breaks/end/", response_model=BreakLogResponse)
def break_end(break_data: BreakClockOut, db: Session = Depends(get_db)):
    """
    End an ongoing break for a given attendance_id and calculate total break time.
    """
    try:
        # Retrieve the most recent ongoing break log for the given attendance_id
        break_log = db.query(BreakLog).filter(
            BreakLog.attendance_id == break_data.attendance_id, 
            BreakLog.break_end == None
        ).order_by(BreakLog.break_start.desc()).first()

        if not break_log:
            raise HTTPException(status_code=404, detail="Ongoing break not found.")

        # Set the break_end time and calculate total_break_time
        break_log.break_end = datetime.now()
        break_duration = (break_log.break_end - break_log.break_start).total_seconds() / 60.0  # Convert to minutes
        break_log.total_break_time = round(break_duration, 2)

        # Commit the changes to the database
        db.commit()
        db.refresh(break_log)

        return break_log

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    

@router.put("/edit/break/start")
def update_break_start(
    body: dict,
    db: Session = Depends(get_db)
):
    try:
        # Extract data from request body
        attendance_id = body.get("attendance_id")
        break_id = body.get("break_id")
        break_start_kst = body.get("break_start")  # Expected as a Korean time string (ISO format)

        if not all([attendance_id, break_id, break_start_kst]):
            raise HTTPException(status_code=400, detail="Invalid or missing input data")

        # Convert KST time string to UTC
        kst_timezone = pytz.timezone("Asia/Seoul")
        utc_timezone = pytz.utc
        break_start_kst_dt = datetime.fromisoformat(break_start_kst)
        break_start_utc_dt = kst_timezone.localize(break_start_kst_dt).astimezone(utc_timezone)

        # Fetch the break log
        break_log = db.query(BreakLog).filter(
            BreakLog.id == break_id,
            BreakLog.attendance_id == attendance_id
        ).first()

        if not break_log:
            raise HTTPException(status_code=404, detail="Break log not found")

        # Update the break_start with the converted UTC time
        break_log.break_start = break_start_utc_dt

        # Fetch the associated attendance log
        attendance = db.query(AttendanceLog).filter(
            AttendanceLog.id == attendance_id
        ).first()

        if not attendance:
            raise HTTPException(status_code=404, detail="Attendance record not found")

        # Calculate the updated total worked hours
        attendance.total_hours = attendance.calculate_total_hours()

        # Commit changes to the database
        db.commit()

        return {
            "message": "Break start time updated successfully",
            "break_log": {
                "id": break_log.id,
                "break_start": break_log.break_start.isoformat(),
            },
            "total_hours": attendance.total_hours,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@router.post("/create/break")
def create_new_break(
    break_data: CreateNewBreak,
    db: Session = Depends(get_db),
):
    try:
        # Fetch the associated attendance log
        attendance = db.query(AttendanceLog).filter(
            AttendanceLog.id == break_data.attendance_id
        ).first()

        if not attendance:
            raise HTTPException(
                status_code=404, detail="Attendance record not found"
            )

        # Define Korean timezone and UTC timezone
        kst_timezone = pytz.timezone("Asia/Seoul")
        utc_timezone = pytz.utc

        # Convert break_start and break_end from Korean time to UTC
        break_start_kst = datetime.fromisoformat(break_data.break_start)
        break_end_kst = datetime.fromisoformat(break_data.break_end)

        break_start_utc = kst_timezone.localize(break_start_kst).astimezone(utc_timezone)
        break_end_utc = kst_timezone.localize(break_end_kst).astimezone(utc_timezone)

        # Calculate the total break time in hours
        total_break_time = (break_end_utc - break_start_utc).total_seconds() / 3600

        if total_break_time < 0:
            raise HTTPException(
                status_code=400, detail="Break end time must be after break start time"
            )

        # Create a new BreakLog instance
        new_break = BreakLog(
            attendance_id=break_data.attendance_id,
            break_type=break_data.break_type,
            break_start=break_start_utc,
            break_end=break_end_utc,
        )

        # Add the new break to the session
        db.add(new_break)

        # Recalculate total hours for the associated attendance log
        attendance.total_hours = attendance.calculate_total_hours()

        # Commit changes to the database
        db.commit()
        db.refresh(new_break)

        return {
            "message": "Break created successfully",
            "break_log": {
                "id": new_break.id,
                "attendance_id": new_break.attendance_id,
                "break_type": new_break.break_type,
                "break_start": new_break.break_start.isoformat(),
                "break_end": new_break.break_end.isoformat(),
                "total_break_time": round(total_break_time, 2),
            },
            "total_hours": round(attendance.total_hours, 2),
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    

@router.delete("/delete/break/{break_id}")
def delete_break(
    break_id: int,
    db: Session = Depends(get_db),
):
    try:
        # Fetch the break log by ID
        break_log = db.query(BreakLog).filter(BreakLog.id == break_id).first()

        if not break_log:
            raise HTTPException(status_code=404, detail="Break log not found")

        # Fetch the associated attendance record
        attendance = db.query(AttendanceLog).filter(
            AttendanceLog.id == break_log.attendance_id
        ).first()

        if not attendance:
            raise HTTPException(
                status_code=404, detail="Associated attendance record not found"
            )

        # Delete the break log
        db.delete(break_log)

        # Recalculate total hours for the associated attendance log
        attendance.total_hours = attendance.calculate_total_hours()

        # Commit the changes
        db.commit()

        return {
            "message": "Break deleted successfully",
            "attendance_id": attendance.id,
            "total_hours": round(attendance.total_hours, 2),
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
