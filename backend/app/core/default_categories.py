"""Базовые категории нового пользователя (FR-10).

Создаются при регистрации, чтобы пользователь мог сразу добавлять операции.
Набор одинаковый для всех; пользователь сможет добавлять и удалять категории
позже (этап Э4).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category

DEFAULT_CATEGORIES = [
    "Продукты",
    "Транспорт",
    "Жильё",
    "Развлечения",
    "Здоровье",
    "Прочее",
]


def seed_default_categories(db: Session, user_id: int) -> None:
    """Добавить стандартный набор категорий в транзакции вызывающего кода."""
    existing = set(
        db.scalars(select(Category.name).where(Category.user_id == user_id))
    )
    for name in DEFAULT_CATEGORIES:
        if name not in existing:
            db.add(Category(user_id=user_id, name=name))
