from sqlalchemy import Column, Integer, TIMESTAMP, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.orm import Session
import pytz
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


    def calculate_total_hours(self):
        """
        Calculate total hours worked based on clock_in and clock_out.
        Assumes datetime values are already in KST.
        """
        if self.clock_in and self.clock_out:
            # Calculate the difference between clock_in and clock_out
            time_diff = self.clock_out - self.clock_in
            total_hours = time_diff.total_seconds() / 3600  # Convert seconds to hours
            return round(total_hours, 2)  # Return rounded to 2 decimal places
        return 0

    def update_total_hours(self, db: Session):
        """
        Update the total_hours field after clock_out is set.
        """
        if self.clock_out:
            self.total_hours = self.calculate_total_hours()
            db.commit()
            db.refresh(self)

