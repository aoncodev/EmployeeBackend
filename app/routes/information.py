from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.information import RestaurantHoursCreate
from app.models.basic_info import RestaurantHours

router = APIRouter(prefix="/restaurant-hours", tags=["Restaurant Hours"])

@router.post("/", response_model=RestaurantHoursCreate, status_code=status.HTTP_201_CREATED)
def create_restaurant_hours(restaurant_hours: RestaurantHoursCreate, db: Session = Depends(get_db)):
    # Check if restaurant hours already exist
    existing_hours = db.query(RestaurantHours).first()
    if existing_hours:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Restaurant hours already exist")

    # Create a new restaurant hours record
    db_restaurant_hours = RestaurantHours(
        opening_time=restaurant_hours.opening_time,
        closing_time=restaurant_hours.closing_time
    )
    db.add(db_restaurant_hours)
    db.commit()
    db.refresh(db_restaurant_hours)
    return db_restaurant_hours