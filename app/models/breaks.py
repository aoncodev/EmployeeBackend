from sqlalchemy import Column, Integer, String, TIMESTAMP, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class BreakLog(Base):
    __tablename__ = 'break_log'

    id = Column(Integer, primary_key=True, index=True)
    attendance_id = Column(Integer, ForeignKey('attendance_log.id', ondelete="CASCADE"), nullable=False)
    break_type = Column(String(50), nullable=False)  # e.g., "eating", "praying", "bathroom"
    break_start = Column(TIMESTAMP, nullable=False)
    break_end = Column(TIMESTAMP, nullable=True)  # Nullable until break ends
    total_break_time = Column(Numeric(10, 2), nullable=True)  # Calculated after break ends (in minutes)
    created_at = Column(TIMESTAMP, default=datetime.now)

    attendance_log = relationship("AttendanceLog", back_populates="break_logs")

    def recalculate_total_break_time(self):
        """
        Recalculate the total break time in minutes based on break_start and break_end.
        If break_end is provided, calculates the difference in minutes (rounded to 2 decimals).
        If break_end is None, total_break_time is set to None.
        """
        if self.break_end and self.break_start:
            delta = self.break_end - self.break_start
            self.total_break_time = round(delta.total_seconds() / 60, 2)
        else:
            self.total_break_time = None
