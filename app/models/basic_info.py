from sqlalchemy import Column, Integer, Time, TIMESTAMP
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.sql import func
from datetime import datetime

class RestaurantHours(Base):
    __tablename__ = 'restaurant_hours'
    id = Column(Integer, primary_key=True, index=True)
    opening_time = Column(Time, nullable=False)
    closing_time = Column(Time, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)