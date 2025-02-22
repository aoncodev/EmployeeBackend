from sqlalchemy import Column, Integer,String, TIMESTAMP, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.orm import Session
import pytz
from datetime import datetime
from sqlalchemy.sql import func
from decimal import Decimal

from app.models.basic_info import RestaurantHours



class LateRecord(Base):
    __tablename__ = 'late_records'
    id = Column(Integer, primary_key=True, index=True)
    attendance_id = Column(Integer, ForeignKey('attendance_log.id', ondelete="CASCADE"), nullable=False)
    late_duration_minutes = Column(Numeric(10, 2), nullable=False)  # Duration of lateness in minutes
    deduction_amount = Column(Numeric(10, 2), nullable=False)  # Deduction amount from hourly wage
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)

    attendance_log = relationship("AttendanceLog", back_populates="late_record")


class Penalty(Base):
    __tablename__ = 'penalties'
    id = Column(Integer, primary_key=True, index=True)
    attendance_id = Column(Integer, ForeignKey('attendance_log.id', ondelete="CASCADE"), nullable=False)
    description = Column(String(255), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)

    attendance_log = relationship("AttendanceLog", back_populates="penalties")

class Bonus(Base):
    __tablename__ = 'bonuses'
    id = Column(Integer, primary_key=True, index=True)
    attendance_id = Column(Integer, ForeignKey('attendance_log.id', ondelete="CASCADE"), nullable=False)
    description = Column(String(255), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)

    attendance_log = relationship("AttendanceLog", back_populates="bonuses")

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
    late_record = relationship("LateRecord", uselist=False, back_populates="attendance_log")  # One-to-One relationship
    penalties = relationship("Penalty", back_populates="attendance_log", cascade="all, delete-orphan")
    bonuses = relationship("Bonus", back_populates="attendance_log", cascade="all, delete-orphan")


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

    def check_if_late(self, db: Session):
        """
        Check if the employee was late based on the restaurant's opening hours.
        If the employee clocked in later than the opening time, calculate the late duration
        and deduction. Otherwise, remove any existing late record.
        """
        restaurant_hours = db.query(RestaurantHours).first()
        if restaurant_hours and self.clock_in:
            clock_in_time = self.clock_in.time()
            opening_time = restaurant_hours.opening_time

            if clock_in_time > opening_time:
                self.is_late = True
                late_duration = datetime.combine(datetime.min, clock_in_time) - datetime.combine(datetime.min, opening_time)
                late_duration_minutes = Decimal(late_duration.total_seconds() / 60)  # Convert seconds to minutes

                # Fetch employee's hourly wage
                employee = self.employee
                hourly_wage = employee.hourly_wage

                # Calculate deduction amount
                deduction_amount = (hourly_wage / Decimal(60)) * late_duration_minutes

                if self.late_record:
                    # Update existing record if present
                    self.late_record.late_duration_minutes = late_duration_minutes
                    self.late_record.deduction_amount = deduction_amount
                else:
                    # Create a new late record if not present
                    late_record = LateRecord(
                        attendance_id=self.id,
                        late_duration_minutes=late_duration_minutes,
                        deduction_amount=deduction_amount
                    )
                    db.add(late_record)
                db.commit()
                db.refresh(self)
            else:
                # Employee is on time or early: remove any existing late record
                self.is_late = False
                if self.late_record:
                    db.delete(self.late_record)
                    db.commit()
                    self.late_record = None
                db.commit()
                db.refresh(self)


    def calculate_net_pay(self):
        """
        Calculate the net pay for this attendance record based on:
        - Total working hours (clock_out - clock_in)
        - Minus total break time
        - Minus late deductions and penalties
        - Plus bonuses
        """
        # 1. Calculate total work hours
        total_work_hours = self.calculate_total_hours()  # in hours

        # 2. Subtract total break time (assumed to be stored in hours in BreakLog.total_break_time)
        total_break_hours = sum(
            float(b.total_break_time) for b in self.break_logs if b.total_break_time is not None
        )
        effective_hours = total_work_hours - total_break_hours

        # 3. Calculate base pay using the employee's hourly wage
        base_pay = effective_hours * float(self.employee.hourly_wage)

        # 4. Get total penalty and bonus adjustments
        total_penalties = sum(float(p.price) for p in self.penalties)
        total_bonuses = sum(float(b.price) for b in self.bonuses)
        # Late deduction from LateRecord, if any
        late_deduction = float(self.late_record.deduction_amount) if self.late_record else 0

        # 5. Calculate net pay:
        # Net pay = base pay - (late deduction + penalties) + bonuses
        net_pay = base_pay - late_deduction - total_penalties + total_bonuses

        return round(net_pay, 2)

