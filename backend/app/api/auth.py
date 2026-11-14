"""Эндпоинты аутентификации (FR-1, FR-2)."""

from fastapi import APIRouter, Depends, Form, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.default_categories import seed_default_categories
from app.core.security import create_access_token, hash_password, verify_password
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, Token
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
        db.commit()
    except IntegrityError:  # гонка двух одинаковых регистраций
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким именем уже существует",
        ) from None
    db.refresh(user)

    seed_default_categories(db, user.id)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Вход, выдача JWT (FR-2)",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    """Проверить учётные данные и выдать access-токен."""
    user = db.scalar(select(User).where(User.username == payload.username))
    # Одинаковый ответ для «нет такого» и «неверный пароль» — не раскрываем данные
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
        )
    settings = get_settings()
    return Token(
        access_token=create_access_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/token", response_model=Token, summary="Получить JWT из формы Swagger")
def login_from_form(
    username: str = Form(min_length=1, max_length=50),
    password: str = Form(min_length=1, max_length=128),
    db: Session = Depends(get_db),
) -> Token:
    """Принять данные формы OAuth2 и применить те же правила входа."""
    return login(LoginRequest(username=username, password=password), db)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Текущий пользователь (доработка по ревью PR #54)",
)
def me(current_user: User = Depends(get_current_user)) -> User:
    """Данные пользователя из токена — фронтенд определяет по ним роль."""
    return current_user
