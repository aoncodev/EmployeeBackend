from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class BreakType(PyEnum):
    EATING = "eating"
    PRAYING = "praying"
    BATHROOM = "bathroom"


class Employee(Base):
    __tablename__ = 'employees'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    phone = Column(String, unique=True, index=True)
    hourly_wage = Column(Float, nullable=False)
    qr_id = Column(String, unique=True, index=True)  

    clock_in_outs = relationship("ClockInOut", back_populates="employee")


class ClockInOut(Base):
    __tablename__ = 'clock_in_outs'

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id'))
    clock_in = Column(DateTime, default=datetime.utcnow)
    clock_out = Column(DateTime, nullable=True)
    total_work_hours = Column(Float, default=0.0)

    employee = relationship("Employee", back_populates="clock_in_outs")
    breaks = relationship("Break", back_populates="clock_in_out")

    @property
    def break_hours(self):
        return sum(b.break_duration for b in self.breaks)


class Break(Base):
    __tablename__ = 'breaks'

    id = Column(Integer, primary_key=True, index=True)
    clock_in_out_id = Column(Integer, ForeignKey('clock_in_outs.id'))
    break_type = Column(Enum(BreakType), nullable=False)
    break_start = Column(DateTime, default=datetime.utcnow)
    break_end = Column(DateTime, nullable=True)

    clock_in_out = relationship("ClockInOut", back_populates="breaks")

    @property
    def break_duration(self):
        if self.break_end:
            return (self.break_end - self.break_start).total_seconds() / 3600
        return 0.0
