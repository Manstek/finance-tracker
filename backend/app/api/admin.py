"""API администратора: управление пользователями (FR-13, NFR-2).

Все эндпоинты требуют is_admin=true, иначе 403.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.db import get_db
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import AdminUserOut, ResetPasswordRequest

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(get_current_admin)])


@router.get(
    "/users",
    response_model=list[AdminUserOut],
    summary="Список пользователей (FR-13)",
)
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)).all())


@router.get(
    "/users/{user_id}",
    response_model=AdminUserOut,
    summary="Профиль пользователя (FR-13)",
)
def get_user(user_id: int, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    return user


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить пользователя (FR-13)",
)
def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> None:
    """Удалить пользователя вместе с его данными (каскад по FK)."""
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Администратор не может удалить себя",
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    db.delete(user)  # категории и операции удалятся каскадно
    db.commit()


@router.post(
    "/users/{user_id}/reset-password",
    response_model=dict[str, str],
    summary="Сбросить пароль пользователя (UC-11)",
)
def reset_password(
    user_id: int,
    payload: ResetPasswordRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Помощь в восстановлении доступа: новый пароль от администратора."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"detail": "Пароль обновлён"}
