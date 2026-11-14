"""Pydantic-схемы пользователя (FR-1, FR-13)."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic import field_validator

from app.core.security import BCRYPT_PASSWORD_MAX_BYTES


class UserCreate(BaseModel):
    """Тело запроса регистрации."""

    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[A-Za-z0-9_-]+$",
        examples=["ivan"],
        description="Латиница, цифры, _ и -",
    )
    password: str = Field(
        min_length=8,
        max_length=BCRYPT_PASSWORD_MAX_BYTES,
        description="Не более 72 байт в UTF-8",
        examples=["12345678"],
    )
    email: str | None = Field(default=None, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_bcrypt_password(cls, password: str) -> str:
        if len(password.encode("utf-8")) > BCRYPT_PASSWORD_MAX_BYTES:
            raise ValueError("Пароль должен занимать не более 72 байт в UTF-8")
        if "\0" in password:
            raise ValueError("Пароль не должен содержать нулевой символ")
        return password


class UserOut(BaseModel):
    """Данные пользователя в ответах API (без хеша пароля)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None = None
    is_admin: bool
