from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.penalty import PenaltyCreate, PenaltyResponse
from app.models.attendance import Penalty

router = APIRouter(prefix="/penalties", tags=["Penalties"])

@router.post("/", response_model=PenaltyCreate, status_code=status.HTTP_201_CREATED)
def create_penalty(penalty: PenaltyCreate, db: Session = Depends(get_db)):
    # Create a new penalty record
    db_penalty = Penalty(
        attendance_id=penalty.attendance_id,
        description=penalty.description,
        price=penalty.price
    )
    db.add(db_penalty)
    db.commit()
    db.refresh(db_penalty)
    return db_penalty

@router.get("/attendance/{attendance_id}", response_model=PenaltyResponse, status_code=status.HTTP_200_OK)
def get_penalty(attendance_id: int, db: Session = Depends(get_db)):
    """
    Get a penalty record by its ID.
    """
    penalty = db.query(Penalty).filter(Penalty.attendance_id == attendance_id).first()
    if not penalty:
        raise HTTPException(status_code=404, detail="Penalty not found")
    return penalty

@router.get("/", response_model=list[PenaltyResponse], status_code=status.HTTP_200_OK)
def get_penalties(db: Session = Depends(get_db)):
    """
    Get all penalty records.
    """
    penalties = db.query(Penalty).all()
    return penalties

@router.delete("/{penalty_id}", status_code=status.HTTP_200_OK)
def delete_penalty(penalty_id: int, db: Session = Depends(get_db)):
    """
    Delete a penalty record by its ID.
    """
    penalty = db.query(Penalty).filter(Penalty.id == penalty_id).first()
    if not penalty:
        raise HTTPException(status_code=404, detail="Penalty not found")
    
    db.delete(penalty)
    db.commit()
    return {"message": "Penalty deleted successfully"}