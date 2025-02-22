from pydantic import BaseModel, Field
from datetime import time

class RestaurantHoursCreate(BaseModel):
    opening_time: time = Field(..., description="Opening time of the restaurant")
    closing_time: time = Field(..., description="Closing time of the restaurant")