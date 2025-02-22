from pydantic import BaseModel, Field

class BonusCreate(BaseModel):
    attendance_id: int = Field(..., description="ID of the attendance log")
    description: str = Field(..., description="Description of the bonus")
    price: float = Field(..., description="Price of the bonus")