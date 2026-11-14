"""Pydantic-схемы аутентификации (FR-2)."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Тело запроса входа. Без ограничений длины — проверка на стороне сервера БД."""

    username: str = Field(min_length=1, max_length=50, examples=["ivan"])
    password: str = Field(min_length=1, max_length=128, examples=["12345678"])


class Token(BaseModel):
    """Ответ с JWT (api.md, FR-2)."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # секунд до истечения токена
