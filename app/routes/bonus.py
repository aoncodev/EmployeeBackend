from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.bonus import BonusCreate
from app.models.attendance import Bonus

router = APIRouter(prefix="/bonuses", tags=["Bonuses"])

@router.post("/", response_model=BonusCreate, status_code=status.HTTP_201_CREATED)
def create_bonus(bonus: BonusCreate, db: Session = Depends(get_db)):
    # Create a new bonus record
    db_bonus = Bonus(
        attendance_id=bonus.attendance_id,
        description=bonus.description,
        price=bonus.price
    )
    db.add(db_bonus)
    db.commit()
    db.refresh(db_bonus)
    return db_bonus

@router.get("/attendance/{attendance_id}", response_model=List[BonusCreate])
def get_bonus_by_attendance_id(attendance_id: int, db: Session = Depends(get_db)):
    """
    Retrieve all bonus records for a given attendance ID.
    """
    bonuses = db.query(Bonus).filter(Bonus.attendance_id == attendance_id).all()
    if not bonuses:
        raise HTTPException(status_code=404, detail="No bonuses found for the given attendance ID")
    return bonuses



@router.delete("/{bonus_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bonus(bonus_id: int, db: Session = Depends(get_db)):
    """
    Delete a bonus record by its bonus ID.
    """
    db_bonus = db.query(Bonus).filter(Bonus.id == bonus_id).first()
    if not db_bonus:
        raise HTTPException(status_code=404, detail="Bonus not found")
    
    db.delete(db_bonus)
    db.commit()
    return None
