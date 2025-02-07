from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.attendance import AttendanceLog
from app.models.employee import Employee
from app.schemas.employee import EmployeeResponse, EmployeeCreate, EmployeeUpdate, EmployeeLogin, RoleEnum
import secrets
import string
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, date, time
from app.models.breaks import BreakLog
from sqlalchemy import or_
import jwt


router = APIRouter()

# Function to generate a random qr_id (e.g., a 20-character alphanumeric string)
def generate_qr_id(length=20):
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


# JWT Configuration
SECRET_KEY = "yourdfsdfdsfdsf_fdsfsdfdssecret_fsdfdsfdfdfwefewsfskey"
ALGORITHM = "HS256"

def create_token(employee_id: int, role: str):
    """
    Create a JWT token with a 1-day expiration.
    """
    payload = {
        "sub": str(employee_id),  # Convert employee_id to a string
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=30),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


@router.get("/validate-token")
def validate_token(Authorization: str = Header(...), db: Session = Depends(get_db)):
    """
    Validates a JWT token and retrieves user details if the token is valid.
    """
    try:
        # Extract token from the Authorization header
        if not Authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization format.")
        token = Authorization.split(" ")[1]
        print(token)

        # Decode the JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(payload)
        user_id: int = payload.get("sub")
        print(user_id)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload.")

        # Fetch the user from the database
        user = db.query(Employee).filter(Employee.id == user_id).first()
        print(user)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        # Return user details if valid
        return {
            "user": {
                "id": user.id,
                "name": user.name,
                "role": user.role.value,  # Ensure role is serialized correctly
            }
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.post("/admin/login")
def admin_login(qr: EmployeeLogin, db: Session = Depends(get_db)):
    try:
        # Decode the QR data to find the employee
        employee = db.query(Employee).filter(Employee.qr_id == qr.qr_id).first()

        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found.")

        # Check if the employee is an admin
        if str(employee.role) != str(RoleEnum.admin):  # Compare enums directly
            print(RoleEnum.admin)
            print(employee.role)
            raise HTTPException(
                status_code=403, detail="Authentication failed. Admin access required."
            )

        # Generate JWT token
        token = create_token(employee.id, employee.role.value)  # Convert role to string for the token

        # Return the response with the token
        response = {
            "id": employee.id,
            "name": employee.name,
            "role": employee.role.value,  # Convert enum to string for JSON response
            "token": token,
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



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
    Get the attendance and break status for an employee using the latest attendance record.
    
    Logic:
      - Determine the "effective" date:
          * If the current time is before 5:00 AM, use yesterday’s date.
          * Otherwise, use today’s date.
      - Query the latest attendance record for the employee.
      - If the record's clock_in falls within the boundaries of the effective day (or, when before 5 AM,
        allow an open attendance record from a previous day), then use that record.
      - If no valid record is found, return a response with attendance set to None.
    """
    try:
        # Ensure the employee exists.
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found.")

        now = datetime.now()

        # Determine the effective date based on current time.
        effective_date = date.today()
        if now.time() < time(5, 0):
            effective_date = date.today() - timedelta(days=1)

        # Boundaries for the effective day.
        start_of_day = datetime.combine(effective_date, datetime.min.time())
        end_of_day = datetime.combine(effective_date + timedelta(days=1), datetime.min.time())

        # Query the latest attendance record for the employee.
        latest_attendance = (
            db.query(AttendanceLog)
            .filter(AttendanceLog.employee_id == employee_id)
            .order_by(desc(AttendanceLog.clock_in))
            .first()
        )

        attendance = None
        if latest_attendance:
            # Check if the attendance's clock_in is within the effective day.
            if start_of_day <= latest_attendance.clock_in < end_of_day:
                attendance = latest_attendance
            # If before 5 AM, allow an open attendance record (clock_out is None) even if it started before
            # the effective day's start. This lets an employee clock out after midnight.
            elif now.time() < time(5, 0) and latest_attendance.clock_out is None:
                attendance = latest_attendance

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

        # Query all break logs associated with the attendance record.
        break_logs = db.query(BreakLog).filter(BreakLog.attendance_id == attendance.id).all()

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
                    "total_break_time": str(timedelta(minutes=float(br.total_break_time)))
                                        if br.total_break_time else None
                } for br in break_logs
            ]
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")





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

            # If attendance is found, process it; otherwise, set status to "Not clocked in"
            if attendance:
                # Get all breaks for today's attendance
                breaks = db.query(BreakLog).filter(BreakLog.attendance_id == attendance.id).all()

                # Calculate total break time in seconds
                total_break_time_seconds = sum(
                    (timedelta(minutes=float(br.total_break_time)).total_seconds() for br in breaks if br.total_break_time),
                    0
                )

                # Convert total break time to float hours
                total_break_time_hours = total_break_time_seconds / 3600  # Convert to hours

                # Calculate worked hours excluding breaks
                total_hours_seconds = float(attendance.total_hours) * 3600 if attendance.total_hours else 0
                worked_hours_seconds = total_hours_seconds - total_break_time_seconds
                worked_hours = worked_hours_seconds / 3600  # Convert back to hours

                # Add employee's status
                employee_statuses.append({
                    "employee": {
                        "id": employee.id,
                        "name": employee.name,
                        "role": employee.role,
                        "wage": employee.hourly_wage
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
                            "total_break_time": str(timedelta(minutes=float(br.total_break_time)))[:-3] if br.total_break_time else None
                        } for br in breaks
                    ],
                    "total_hours_excluding_breaks": round(worked_hours, 2),  # Add worked hours excluding breaks
                    "total_break_time": round(total_break_time_hours, 2)  # Add total break time as float hours
                })
            else:
                # If no attendance record, mark employee as not clocked in
                employee_statuses.append({
                    "employee": {
                        "id": employee.id,
                        "name": employee.name,
                        "role": employee.role,
                        "wage": employee.hourly_wage
                    },
                    "attendance": None,  # No attendance for this date
                    "breaks": [],
                    "total_hours_excluding_breaks": 0.0,  # No work hours
                    "total_break_time": 0.0  # No break time
                })

        return {"employees": employee_statuses}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



