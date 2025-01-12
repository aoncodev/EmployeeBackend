from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.attendance import AttendanceLog
from app.models.employee import Employee
from app.schemas.employee import EmployeeResponse, EmployeeCreate, EmployeeUpdate, EmployeeLogin
import secrets
import string
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, date
from app.models.breaks import BreakLog
router = APIRouter()

# Function to generate a random qr_id (e.g., a 20-character alphanumeric string)
def generate_qr_id(length=20):
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))



# Endpoint to get all employees
@router.get("/employees", response_model=List[EmployeeResponse])
def get_all_employees(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()
    return employees




@router.post("/employee", response_model=EmployeeResponse)
def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
    try:
        # Generate a random QR ID for the employee
        qr_id = generate_qr_id()

        # Create a new employee instance with the generated QR ID
        db_employee = Employee(
            name=employee.name,
            role=employee.role,
            qr_id=qr_id,  # Automatically generated QR ID
            hourly_wage=employee.hourly_wage
        )

        # Add to session and commit to save
        db.add(db_employee)
        db.commit()
        db.refresh(db_employee)  # Retrieve the newly created employee with ID

        return db_employee
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="QR Badge ID already exists.")
    

@router.put("/employee/{id}", response_model=EmployeeResponse)
def update_employee(id: int, employee_update: EmployeeUpdate, db: Session = Depends(get_db)):
    # Fetch the employee based on the provided qr_id
    db_employee = db.query(Employee).filter(Employee.id == id).first()

    if not db_employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Update fields if provided
    if employee_update.name:
        db_employee.name = employee_update.name
    if employee_update.hourly_wage:
        db_employee.hourly_wage = employee_update.hourly_wage
    
    # Commit the changes to the database
    db.commit()

    # Refresh the instance to reflect the changes
    db.refresh(db_employee)

    return db_employee

@router.delete("/employee/{id}")
def remove_employee(id: int, db: Session = Depends(get_db)):
    # Fetch the employee record
    db_employee = db.query(Employee).filter(Employee.id == id).first()

    if not db_employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Delete the employee record (cascading deletes will handle related records)
    db.delete(db_employee)
    db.commit()

    return {"message": f"Employee with ID {id} has been successfully deleted"}




@router.post("/login")
def login(qr: EmployeeLogin, db: Session = Depends(get_db)):
    try:
        # Decode the QR data (expected to be the employee's unique identifier)
        print(qr.qr_id)
        employee = db.query(Employee).filter(Employee.qr_id == qr.qr_id).first()

        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found.")

        # Get today's attendance record for the employee
        today_date = datetime.today().date()

        today_attendance = db.query(AttendanceLog).filter(
            AttendanceLog.employee_id == employee.id,
            AttendanceLog.clock_in >= today_date
        ).first()

        # Prepare the response with employee details and attendance status
        response = {
                "id": employee.id,
                "name": employee.name,
                "role": employee.role
            }
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    


@router.get("/employee/status/{employee_id}")
def get_employee_status(employee_id: int, db: Session = Depends(get_db)):
    """
    Get today's attendance and break status for an employee.
    """
    try:
        # Check if the employee exists
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found.")

        # Get today's date
        today_date = datetime.today().date()

        # Fetch today's attendance for the employee
        attendance = db.query(AttendanceLog).filter(
            AttendanceLog.employee_id == employee_id,
            AttendanceLog.clock_in >= today_date
        ).first()

        if not attendance:
            return {
                "employee": {
                    "id": employee.id,
                    "name": employee.name,
                    "role": employee.role
                },
                "attendance": None,
                "breaks": []
            }

        # Fetch all breaks associated with today's attendance
        breaks = db.query(BreakLog).filter(
            BreakLog.attendance_id == attendance.id
        ).all()

        # Prepare the response
        response = {
            "employee": {
                "id": employee.id,
                "name": employee.name,
                "position": employee.role
            },
            "attendance": {
                "id": attendance.id,
                "clock_in": attendance.clock_in,
                "clock_out": attendance.clock_out,
                "total_hours": attendance.total_hours,
                "created_at": attendance.created_at
            },
            "breaks": [
                {
                    "id": br.id,
                    "break_type": br.break_type,
                    "break_start": br.break_start,
                    "break_end": br.break_end,
                    "total_break_time": str(timedelta(minutes=float(br.total_break_time))) if br.total_break_time else None
                } for br in breaks
            ]
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

from datetime import timedelta

@router.get("/employees/status/")
def get_all_employees_status(date: date = None, db: Session = Depends(get_db)):
    """
    Get attendance and break status for all employees for a given date (default to today).
    """
    try:
        # If no date is provided, use today's date
        date = date or datetime.today().date()

        # Retrieve all employees
        employees = db.query(Employee).all()
        if not employees:
            raise HTTPException(status_code=404, detail="No employees found.")

        employee_statuses = []

        for employee in employees:
            # Get today's attendance for the employee based on the provided or default date
            attendance = (
                db.query(AttendanceLog)
                .filter(
                    AttendanceLog.employee_id == employee.id,
                    AttendanceLog.clock_in >= datetime(date.year, date.month, date.day),
                    AttendanceLog.clock_in < datetime(date.year, date.month, date.day) + timedelta(days=1)
                )
                .first()
            )

            # If no attendance is found, skip this employee
            if not attendance or not attendance.clock_in or not attendance.clock_out:
                continue

            # Get all breaks for today's attendance
            breaks = []
            total_break_time_seconds = 0  # To accumulate total break time in seconds
            if attendance:
                breaks = (
                    db.query(BreakLog)
                    .filter(BreakLog.attendance_id == attendance.id)
                    .all()
                )
                # Calculate total break time in seconds
                for br in breaks:
                    # Assuming total_break_time is in string format like '0:00:09'
                    break_time = timedelta(minutes=float(br.total_break_time))
                    total_break_time_seconds += break_time.total_seconds()

            # Convert total break time to float hours
            total_break_time_hours = total_break_time_seconds / 3600  # Convert to hours

            # Convert total_hours to float for consistency, if available
            total_hours_seconds = float(attendance.total_hours) * 3600 if attendance.total_hours else 0  # Convert to seconds
            worked_hours_seconds = total_hours_seconds - total_break_time_seconds
            worked_hours = worked_hours_seconds / 3600  # Convert back to hours

            # Prepare employee's status
            employee_statuses.append({
                "employee": {
                    "id": employee.id,
                    "name": employee.name,
                    "role": employee.role,
                    "wage": employee.hourly_wage
                },
                "attendance": {
                    "id": attendance.id if attendance else None,
                    "clock_in": attendance.clock_in if attendance else None,
                    "clock_out": attendance.clock_out if attendance else None,
                    "total_hours": attendance.total_hours if attendance else None,
                    "created_at": attendance.created_at if attendance else None
                },
                "breaks": [
                    {
                        "id": br.id,
                        "break_type": br.break_type,
                        "break_start": br.break_start,
                        "break_end": br.break_end,
                        "total_break_time": str(timedelta(minutes=float(br.total_break_time)))[:-3] if br.total_break_time else None
                    } for br in breaks
                ],
                "total_hours_excluding_breaks": round(worked_hours, 2),  # Add worked hours excluding breaks
                "total_break_time": round(total_break_time_hours, 2)  # Add total break time as float hours
                
            })

        return {"employees": employee_statuses}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


