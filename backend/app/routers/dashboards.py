from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/{user_id}", response_model=schemas.DashboardRead)
def get_user_dashboard(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    current_book = None
    next_book = None

    if user.current_book_id:
        current_book = db.query(models.Book).filter(models.Book.id == user.current_book_id).first()
    if user.next_book_id:
        next_book = db.query(models.Book).filter(models.Book.id == user.next_book_id).first()

    return {
        "user": user,
        "current_book": current_book,
        "next_book": next_book,
    }
