from sqlalchemy import Column, Integer, TIMESTAMP, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class AttendanceLog(Base):
    __tablename__ = 'attendance_log'

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id', ondelete="CASCADE"), nullable=False)
    clock_in = Column(TIMESTAMP, nullable=False)
    clock_out = Column(TIMESTAMP, nullable=True)  # Nullable until clock out
    total_hours = Column(Numeric(10, 2), nullable=True)  # Calculated after clock-out
    created_at = Column(TIMESTAMP, default=datetime.now)

    # Corrected relationship
    employee = relationship("Employee", back_populates="attendance_logs")

    # BreakLog remains unchanged
    break_logs = relationship("BreakLog", back_populates="attendance_log", cascade="all, delete-orphan")
