from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/comments", tags=["comments"])


@router.post("", response_model=schemas.CommentRead)
def create_comment(payload: schemas.CommentCreate, db: Session = Depends(get_db)):
    comment = models.Comment(
        underline_id=payload.underline_id,
        user_id=payload.user_id,
        content=payload.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.get("/underline/{underline_id}", response_model=list[schemas.CommentRead])
def list_underline_comments(underline_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Comment)
        .filter(models.Comment.underline_id == underline_id)
        .order_by(models.Comment.id.asc())
        .all()
    )
