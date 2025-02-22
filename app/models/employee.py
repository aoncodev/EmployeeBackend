from sqlalchemy import Column, Integer, String, Numeric, TIMESTAMP, Enum
from sqlalchemy.orm import relationship
from app.models.attendance import AttendanceLog  # Ensure AttendanceLog is imported
from datetime import datetime
from app.database import Base
from enum import Enum as PyEnum

# Enum class for role
class RoleEnum(PyEnum):
    admin = "admin"
    employee = "employee"

class Employee(Base):
    __tablename__ = 'employees'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)  # Role can be 'admin' or 'employee'
    qr_id = Column(String(20), unique=True, nullable=False)  # QR badge ID
    hourly_wage = Column(Numeric(10, 2), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.now)

    attendance_logs = relationship("AttendanceLog", back_populates="employee", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="employee", cascade="all, delete-orphan")

