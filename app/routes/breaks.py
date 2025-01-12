from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.attendance import AttendanceLog
from app.models.employee import Employee
from app.models.breaks import BreakLog
from app.schemas.breaks import BreakLogBase, BreakLogResponse, BreakClockIn, BreakClockOut
from datetime import datetime, date
from typing import Optional

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