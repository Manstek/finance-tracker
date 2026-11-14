"""Pydantic-схемы финансовых операций (FR-3..FR-8)."""

from datetime import date as date_type
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


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
