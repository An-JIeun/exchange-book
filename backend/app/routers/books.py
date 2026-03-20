from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/books", tags=["books"])


@router.post("", response_model=schemas.BookRead)
def create_book(payload: schemas.BookCreate, db: Session = Depends(get_db)):
    book = models.Book(title=payload.title, author=payload.author, cover_url=payload.cover_url)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.get("", response_model=list[schemas.BookRead])
def list_books(db: Session = Depends(get_db)):
    return db.query(models.Book).all()
