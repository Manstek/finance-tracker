"""Pydantic-схемы финансовых операций (FR-3..FR-8)."""

from datetime import date as date_type
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator


class TransactionCreate(BaseModel):
    """Тело запроса добавления операции (FR-4)."""

    type: Literal["income", "expense"]
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2, examples=[1500.00])
    category_id: int | None = None
    date: date_type = Field(examples=["2026-11-02"])
    comment: str | None = Field(default=None, max_length=500)


class TransactionOut(BaseModel):
    """Операция в ответах API; сумма — строка с двумя знаками (api.md)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    amount: Decimal
    category_id: int | None = None
    date: date_type
    comment: str | None = None

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> str:
        return f"{value.quantize(Decimal('0.01'))}"


class TransactionUpdate(BaseModel):
    """Изменить только явно переданные поля операции."""

    type: Literal["income", "expense"] | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    category_id: int | None = None
    date: date_type | None = None
    comment: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_non_nullable_values(self):
        for field in ("type", "amount", "date"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"Поле {field} не может быть пустым")
        return self


class Totals(BaseModel):
    """Итоги за период (FR-7)."""

    income: str
    expense: str
    balance: str


class OperationList(BaseModel):
    """Ответ списка операций: страница + итоги за период фильтра (FR-5, FR-7)."""

    items: list[TransactionOut]
    totals: Totals
    page: int
    per_page: int
    total: int
