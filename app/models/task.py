from sqlalchemy import Column, Integer, String, Boolean, Date, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    task_date = Column(Date, nullable=False)
    status = Column(Boolean, default=False, nullable=False)  # False for incomplete, True for complete
    completed_at = Column(TIMESTAMP, nullable=True)

    # Define a relationship with the Employee model (optional)
    employee = relationship("Employee", back_populates="tasks")
