"""Общие зависимости FastAPI: текущий пользователь и администратор."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models.user import User

# Swagger UI отправляет учётные данные формой (/docs → Authorize).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Не авторизован или токен истёк",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Декодировать JWT и вернуть пользователя; иначе 401."""
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_error
    user = db.get(User, user_id)
    if user is None:
        raise credentials_error
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """Проверить роль администратора (FR-13, NFR-2); иначе 403."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора",
        )
    return user
