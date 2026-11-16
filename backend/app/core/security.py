"""Хеширование и проверка паролей (FR-1).

Пароль никогда не хранится в открытом виде — только bcrypt-хеш.
"""

from passlib.context import CryptContext

# bcrypt — стандарт для хранения паролей (ЛР 1, NFR-1)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Хешировать пароль для хранения в БД."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Проверить, что пароль соответствует сохранённому хешу."""
    return pwd_context.verify(plain_password, password_hash)
