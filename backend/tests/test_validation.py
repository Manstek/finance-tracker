"""Тесты серверной валидации и единого формата ошибок (FR-12, задача #26)."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app

PASSWORD = "local-test-password"


def account(client: TestClient, name: str) -> dict[str, str]:
    data = {"username": name, "password": PASSWORD}
    response = client.post("/api/v1/auth/register", json=data)
    assert response.status_code == 201, response.text
    login = client.post("/api/v1/auth/login", json=data)
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_validation_errors_are_human_readable():
    """422 по телу запроса: сообщения на русском, без англоязычного технического мусора."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={"username": "!", "password": "12", "email": "x" * 300},
        )
        assert response.status_code == 422, response.text
        detail = response.json()["detail"]
        assert isinstance(detail, str)
        for label in ("Имя пользователя", "Пароль", "Email"):
            assert label in detail, detail
        assert "String should have" not in detail  # нет сырых сообщений Pydantic


def test_operation_validation_messages():
    """422 на операции: понятные сообщения для суммы, типа и даты."""
    with TestClient(app) as client:
        headers = account(client, "validation_ops")
        today = date.today().isoformat()

        # Отрицательная сумма
        response = client.post(
            "/api/v1/operations",
            headers=headers,
            json={"type": "expense", "amount": -5, "date": today},
        )
        assert response.status_code == 422, response.text
        assert "Сумма" in response.json()["detail"]

        # Неверный тип
        response = client.post(
            "/api/v1/operations",
            headers=headers,
            json={"type": "transfer", "amount": 5, "date": today},
        )
        assert response.status_code == 422, response.text
        assert "Тип операции" in response.json()["detail"]

        # Некорректная дата в теле
        response = client.post(
            "/api/v1/operations",
            headers=headers,
            json={"type": "expense", "amount": 5, "date": "31.12.2026"},
        )
        assert response.status_code == 422, response.text
        assert "Дата" in response.json()["detail"]


def test_operation_business_errors():
    """Бизнес-ошибки остаются 400/404 с понятным detail (FR-12, api.md)."""
    with TestClient(app) as client:
        headers = account(client, "business_errors")
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        # Будущая дата → 400
        response = client.post(
            "/api/v1/operations",
            headers=headers,
            json={"type": "expense", "amount": 5, "date": tomorrow},
        )
        assert response.status_code == 400, response.text
        assert response.json()["detail"] == "Дата не может быть в будущем"

        # Чужая категория → 404
        response = client.post(
            "/api/v1/operations",
            headers=headers,
            json={"type": "expense", "amount": 5, "date": today, "category_id": 99999},
        )
        assert response.status_code == 404, response.text

        # Чужая операция при PATCH/DELETE → 404
        assert client.patch(
            "/api/v1/operations/99999", headers=headers, json={"amount": 2}
        ).status_code == 404
        assert client.delete("/api/v1/operations/99999", headers=headers).status_code == 404


def test_error_format_is_detail_string():
    """Любая ошибка API — {"detail": строка} (формат из api.md)."""
    with TestClient(app) as client:
        # 401 без токена
        response = client.get("/api/v1/operations")
        assert response.status_code == 401
        assert isinstance(response.json()["detail"], str)

        # 404 несуществующий маршрут
        response = client.get("/api/v1/no-such-endpoint")
        assert response.status_code == 404
        assert "detail" in response.json()

        # 409 занятый username
        account(client, "dup_check")
        response = client.post(
            "/api/v1/auth/register", json={"username": "dup_check", "password": PASSWORD}
        )
        assert response.status_code == 409
        assert isinstance(response.json()["detail"], str)
