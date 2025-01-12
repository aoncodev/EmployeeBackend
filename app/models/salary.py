from sqlalchemy import Column, Integer, Numeric, TIMESTAMP, ForeignKey
from app.database import Base
from datetime import datetime

class SalaryLog(Base):
    __tablename__ = 'salary_log'

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    attendance_id = Column(Integer, ForeignKey('attendance_log.id'), nullable=False)
    total_hours_worked = Column(Numeric(10, 2), nullable=True)
    total_salary = Column(Numeric(10, 2), nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.now)
