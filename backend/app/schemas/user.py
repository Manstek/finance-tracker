"""Pydantic-схемы пользователя (FR-1, FR-13)."""

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    """Тело запроса регистрации."""

    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[A-Za-z0-9_-]+$",
        examples=["ivan"],
        description="Латиница, цифры, _ и -",
    )
    password: str = Field(min_length=8, max_length=128, examples=["12345678"])
    email: str | None = Field(default=None, max_length=255)


class UserOut(BaseModel):
    """Данные пользователя в ответах API (без хеша пароля)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None = None
    is_admin: bool
