"""Создание первого администратора (FR-13).

Запуск из каталога backend:
    python -m scripts.create_admin <username>            # пароль интерактивно
    python -m scripts.create_admin <username> -p Пароль  # неинтерактивно
Если пользователь уже существует — повышает его до администратора.
"""

import argparse
import getpass
import sys

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser(description="Создать администратора")
    parser.add_argument("username")
    parser.add_argument("-p", "--password", help="пароль (иначе запрашивается интерактивно)")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Пароль (минимум 8 символов): ")
    if len(password) < 8:
        print("Ошибка: пароль должен быть не короче 8 символов")
        raise SystemExit(1)

    username = args.username.strip()

    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
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
