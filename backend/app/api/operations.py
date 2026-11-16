"""Эндпоинты финансовых операций (FR-3..FR-5, FR-7).

Изоляция данных (FR-3): каждый запрос фильтруется по user_id текущего
пользователя; чужие объекты отвечают 404 — как несуществующие (NFR-2).
"""

import calendar
from datetime import date
from decimal import Decimal

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import OperationList, TransactionCreate, TransactionOut, Totals

router = APIRouter(prefix="/operations", tags=["Operations"])


def default_period() -> tuple[date, date]:
    """Текущий месяц, когда фильтры дат не заданы (api.md, FR-5)."""
    today = date.today()
    month_end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    return today.replace(day=1), month_end


def get_own_operation(
    operation_id: int, user: User, db: Session
) -> Transaction:
    """Своя операция или 404 — чужие не отличаются от несуществующих (NFR-2)."""
    operation = db.get(Transaction, operation_id)
    if operation is None or operation.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Операция не найдена",
        )
    return operation


@router.post(
    "",
    response_model=TransactionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить операцию (FR-4)",
)
def create_operation(
    payload: TransactionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Transaction:
    """Добавить операцию; категория должна принадлежать пользователю."""
    if payload.date > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Дата не может быть в будущем",
        )
    if payload.category_id is not None:
        category = db.get(Category, payload.category_id)
        if category is None or category.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Категория не найдена",
            )

    operation = Transaction(
        user_id=user.id,
        type=payload.type,
        amount=payload.amount,
        category_id=payload.category_id,
        date=payload.date,
        comment=payload.comment,
    )
    db.add(operation)
    db.commit()
    db.refresh(operation)
    return operation


@router.get(
    "",
    response_model=OperationList,
    summary="Список операций с фильтрами и итогами (FR-5..FR-7)",
)
def list_operations(
    date_from: date | None = None,
    date_to: date | None = None,
    type: Literal["income", "expense"] | None = None,  # noqa: A002 — имя из контракта
    category_id: int | None = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OperationList:
    """Свои операции за период, сортировка по дате по убыванию, пагинация.

    totals считаются по всем операциям фильтра, а не только по странице.
    """
    if date_from is None and date_to is None:
        date_from, date_to = default_period()

    filters = [Transaction.user_id == user.id]
    if date_from is not None:
        filters.append(Transaction.date >= date_from)
    if date_to is not None:
        filters.append(Transaction.date <= date_to)
    if type is not None:
        filters.append(Transaction.type == type)
    if category_id is not None:
        filters.append(Transaction.category_id == category_id)

    base = select(Transaction).where(*filters)

    total = db.scalar(select(func.count()).select_from(Transaction).where(*filters)) or 0
    items = db.scalars(
        base.order_by(Transaction.date.desc(), Transaction.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()

    # Итоги считаем по всем операциям фильтра (не только по странице, FR-7)
    income, expense = db.execute(
        select(
            func.coalesce(func.sum(case((Transaction.type == "income", Transaction.amount))), 0),
            func.coalesce(func.sum(case((Transaction.type == "expense", Transaction.amount))), 0),
        ).where(*filters)
    ).one()
    income, expense = Decimal(income), Decimal(expense)

    return OperationList(
        items=[TransactionOut.model_validate(op) for op in items],
        totals=Totals(
            income=f"{income.quantize(Decimal('0.01'))}",
            expense=f"{expense.quantize(Decimal('0.01'))}",
            balance=f"{(income - expense).quantize(Decimal('0.01'))}",
        ),
        page=page,
        per_page=per_page,
        total=total,
    )


@router.get(
    "/summary",
    response_model=Totals,
    summary="Итоги за период: доходы, расходы, баланс (FR-7)",
)
def summary_operations(
    date_from: date | None = None,
    date_to: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Totals:
    """Суммы доходов и расходов за период; без фильтров — текущий месяц."""
    if date_from is None and date_to is None:
        date_from, date_to = default_period()

    filters = [Transaction.user_id == user.id]
    if date_from is not None:
        filters.append(Transaction.date >= date_from)
    if date_to is not None:
        filters.append(Transaction.date <= date_to)

    income, expense = db.execute(
        select(
            func.coalesce(func.sum(case((Transaction.type == "income", Transaction.amount))), 0),
            func.coalesce(func.sum(case((Transaction.type == "expense", Transaction.amount))), 0),
        ).where(*filters)
    ).one()
    income, expense = Decimal(income), Decimal(expense)

    return Totals(
        income=f"{income.quantize(Decimal('0.01'))}",
        expense=f"{expense.quantize(Decimal('0.01'))}",
        balance=f"{(income - expense).quantize(Decimal('0.01'))}",
    )


@router.delete(
    "/{operation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить операцию (FR-5)",
)
def delete_operation(
    operation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Удалить свою операцию; чужая → 404."""
    operation = get_own_operation(operation_id, user, db)
    db.delete(operation)
    db.commit()
