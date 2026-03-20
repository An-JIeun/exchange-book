from fastapi import APIRouter, Depends, HTTPException
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


@router.delete("/{comment_id}")
def delete_comment(comment_id: int, db: Session = Depends(get_db)):
    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    db.delete(comment)
    db.commit()
    return {"ok": True}
