"""Хеширование паролей и JWT-токены (FR-1, FR-2, NFR-1).

Пароль никогда не хранится в открытом виде — только bcrypt-хеш.
Токены stateless, подпись HS256, короткий срок жизни.
"""

from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

# bcrypt — стандарт для хранения паролей (ЛР 1, NFR-1)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Хешировать пароль для хранения в БД."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Проверить, что пароль соответствует сохранённому хешу."""
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(user_id: int) -> str:
    """Выдать JWT доступа (sub = id пользователя, NFR-1)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    """Декодировать токен; вернуть id пользователя или None, если токен невалиден/истёк."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
