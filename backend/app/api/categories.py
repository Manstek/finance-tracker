from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import Category, User

router = APIRouter(prefix="/categories", tags=["Categories"])


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


@router.get("", response_model=list[CategoryOut])
def list_categories(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Category]:
    return list(db.scalars(select(Category).where(Category.user_id == user.id).order_by(Category.name)))
