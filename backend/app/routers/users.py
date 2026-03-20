import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/users", tags=["users"])


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


@router.post("", response_model=schemas.UserRead)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.nickname == payload.nickname).first()
    if existing:
        raise HTTPException(status_code=409, detail="Nickname already exists")

    user = models.User(
        nickname=payload.nickname,
        password_hash=_hash_password(payload.password),
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/signup", response_model=schemas.UserRead)
def signup_user(payload: schemas.UserSignup, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.nickname == payload.nickname).first()
    if existing:
        raise HTTPException(status_code=409, detail="Nickname already exists")

    has_users = db.query(models.User.id).first() is not None
    user = models.User(
        nickname=payload.nickname,
        password_hash=_hash_password(payload.password),
        is_admin=not has_users,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.UserRead)
def login_user(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.nickname == payload.nickname).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.password_hash:
        raise HTTPException(status_code=403, detail="Password is not set for this account")

    if user.password_hash != _hash_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return user


@router.get("", response_model=list[schemas.UserRead])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()


@router.patch("/{user_id}/dashboard", response_model=schemas.UserRead)
def update_user_dashboard(user_id: int, payload: schemas.UserDashboardUpdate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.current_book_id = payload.current_book_id
    user.current_page = payload.current_page
    user.next_book_id = payload.next_book_id
    db.commit()
    db.refresh(user)
    return user
