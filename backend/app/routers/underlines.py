from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/underlines", tags=["underlines"])


@router.post("", response_model=schemas.UnderlineRead)
def create_underline(payload: schemas.UnderlineCreate, db: Session = Depends(get_db)):
    underline = models.Underline(
        book_id=payload.book_id,
        user_id=payload.user_id,
        page=payload.page,
        content=payload.content,
        is_public=payload.is_public,
    )
    db.add(underline)
    db.commit()
    db.refresh(underline)
    return underline


@router.get("/book/{book_id}", response_model=list[schemas.UnderlineRead])
def list_book_underlines(book_id: int, page: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Underline).filter(models.Underline.book_id == book_id)
    if page is not None:
        query = query.filter(models.Underline.page == page)
    return query.order_by(models.Underline.page.asc()).all()
