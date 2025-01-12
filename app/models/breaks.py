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
    total_break_time = Column(Numeric(10, 2), nullable=True)  # Calculated after break ends
    created_at = Column(TIMESTAMP, default=datetime.now)

    attendance_log = relationship("AttendanceLog", back_populates="break_logs")
