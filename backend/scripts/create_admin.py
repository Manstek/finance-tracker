"""Создание первого администратора (FR-13).

Запуск из каталога backend:
    python -m scripts.create_admin <username>            # пароль интерактивно
    python -m scripts.create_admin <username> -p Пароль  # неинтерактивно
Если пользователь уже существует — повышает его до администратора.
"""

import argparse
import getpass

from pydantic import ValidationError

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import ResetPasswordRequest


def main() -> None:
    parser = argparse.ArgumentParser(description="Создать администратора")
    parser.add_argument("username")
    parser.add_argument("-p", "--password", help="пароль (иначе запрашивается интерактивно)")
    args = parser.parse_args()

    username = args.username.strip()

    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            password = args.password
            if password is None:
                password = getpass.getpass("Пароль (от 8 символов, до 72 байт в UTF-8): ")
            try:
                ResetPasswordRequest(new_password=password)
            except ValidationError:
                print(
                    "Ошибка: пароль должен содержать от 8 символов, занимать не более "
                    "72 байт в UTF-8 и не содержать нулевой символ"
                )
                raise SystemExit(1) from None
            user = User(username=username, password_hash=hash_password(password), is_admin=True)
            db.add(user)
            action = "создан"
        else:
            user.is_admin = True
            action = "повышен до администратора"
        db.commit()

    print(f"Пользователь «{username}» {action}.")


if __name__ == "__main__":
    main()
