"""Эндпоинты аутентификации (FR-1, FR-2)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.default_categories import seed_default_categories
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация по юзернейму и паролю (FR-1)",
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """Создать пользователя и выдать ему базовый набор категорий."""
    username = payload.username.strip()
    email = payload.email.strip() if payload.email else None

    with db.begin():
        exists = db.scalar(select(User).where(User.username == username))
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким именем уже существует",
            )
        if email:
            email_taken = db.scalar(select(User).where(User.email == email))
            if email_taken:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Пользователь с таким email уже существует",
                )

        user = User(
            username=username,
            email=email,
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        try:
            db.flush()
        except IntegrityError:  # гонка двух одинаковых регистраций
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Имя пользователя или email уже заняты",
            ) from None
        seed_default_categories(db, user.id)

    return user
