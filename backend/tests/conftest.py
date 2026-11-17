import os

import pytest


def pytest_configure(config):
    test_url = os.environ.get("FINANCE_TEST_DATABASE_URL")
    if not test_url:
        raise pytest.UsageError("Укажите FINANCE_TEST_DATABASE_URL для отдельной тестовой БД.")
    os.environ["DATABASE_URL"] = test_url


@pytest.fixture(autouse=True)
def isolate_test_data():
    from sqlalchemy import text

    from app.core.db import SessionLocal

    yield
    # Тесты и CLI создают записи в отдельных подключениях к выделенной БД.
    with SessionLocal.begin() as db:
        db.execute(text("TRUNCATE TABLE transactions, categories, users RESTART IDENTITY"))
