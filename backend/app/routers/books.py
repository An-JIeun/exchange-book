from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/books", tags=["books"])


@router.post("", response_model=schemas.BookRead)
def create_book(payload: schemas.BookCreate, db: Session = Depends(get_db)):
    book = models.Book(
        title=payload.title,
        author=payload.author,
        cover_url=payload.cover_url,
        total_pages=payload.total_pages,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.get("", response_model=list[schemas.BookRead])
def list_books(db: Session = Depends(get_db)):
    return db.query(models.Book).all()


@router.delete("/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    db.query(models.Underline).filter(models.Underline.book_id == book_id).update(
        {models.Underline.book_id: None},
        synchronize_session=False,
    )

    db.delete(book)
    db.commit()
    return {"ok": True}
