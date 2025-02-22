from pydantic import BaseModel, Field
from datetime import datetime

class PenaltyCreate(BaseModel):
    attendance_id: int = Field(..., description="ID of the attendance log")
    description: str = Field(..., description="Description of the penalty")
    price: float = Field(..., description="Price of the penalty")

class PenaltyResponse(PenaltyCreate):
    id: int = Field(..., description="ID of the penalty")
    created_at: datetime = Field(..., description="Timestamp of when the penalty was created")