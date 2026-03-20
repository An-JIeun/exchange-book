from fastapi import APIRouter, Depends, HTTPException
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
    db.flush()

    if payload.initial_comment and payload.initial_comment.strip():
        first_comment = models.Comment(
            underline_id=underline.id,
            user_id=payload.user_id,
            content=payload.initial_comment.strip(),
        )
        db.add(first_comment)

    db.commit()
    db.refresh(underline)
    return underline


@router.get("/book/{book_id}", response_model=list[schemas.UnderlineRead])
def list_book_underlines(book_id: int, page: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Underline).filter(models.Underline.book_id == book_id)
    if page is not None:
        query = query.filter(models.Underline.page == page)
    return query.order_by(models.Underline.page.asc()).all()


@router.delete("/{underline_id}")
def delete_underline(underline_id: int, db: Session = Depends(get_db)):
    underline = db.query(models.Underline).filter(models.Underline.id == underline_id).first()
    if not underline:
        raise HTTPException(status_code=404, detail="Underline not found")

    db.delete(underline)
    db.commit()
    return {"ok": True}
