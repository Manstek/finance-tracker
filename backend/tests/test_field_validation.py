"""Тесты нормализации и валидации полей (FR-12, задача #26)."""

from datetime import date

from fastapi.testclient import TestClient

from app.main import app

PASSWORD = "local-test-password"


def account(client: TestClient, name: str, **extra) -> dict[str, str]:
    data = {"username": name, "password": PASSWORD, **extra}
    response = client.post("/api/v1/auth/register", json=data)
    assert response.status_code == 201, response.text
    login = client.post(
        "/api/v1/auth/login", json={"username": data["username"], "password": PASSWORD}
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_email_format_validation():
    """Некорректный email → 422 с понятным сообщением; корректный нормализуется."""
    with TestClient(app) as client:
        for bad in ("ivan@@example", "ivan example.com", "ivan@", "@example.com", "ivan@example"):
            response = client.post(
                "/api/v1/auth/register",
                json={"username": "email_bad", "password": PASSWORD, "email": bad},
            )
            assert response.status_code == 422, response.text
            assert "Email" in response.json()["detail"]

        response = client.post(
            "/api/v1/auth/register",
            json={"username": "email_ok", "password": PASSWORD, "email": "  Ivan@Example.COM "},
        )
        assert response.status_code == 201, response.text
        assert response.json()["email"] == "ivan@example.com"  # обрезан и приведён к нижнему регистру


def test_username_is_stripped():
    """Пробелы вокруг username обрезаются до проверки уникальности."""
    with TestClient(app) as client:
        assert client.post(
            "/api/v1/auth/register", json={"username": "  spaced  ", "password": PASSWORD}
        ).status_code == 201
        # Тот же username без пробелов — уже занят
        assert client.post(
            "/api/v1/auth/register", json={"username": "spaced", "password": PASSWORD}
        ).status_code == 409


def test_comment_is_normalized():
    """Пустой комментарий (после обрезки пробелов) сохраняется как NULL."""
    with TestClient(app) as client:
        headers = account(client, "comment_user")
        today = date.today().isoformat()

        response = client.post(
            "/api/v1/operations",
            headers=headers,
            json={"type": "expense", "amount": 10, "date": today, "comment": "  продукты  "},
        )
        assert response.status_code == 201, response.text
        assert response.json()["comment"] == "продукты"

        response = client.post(
            "/api/v1/operations",
            headers=headers,
            json={"type": "expense", "amount": 11, "date": today, "comment": "   "},
        )
        assert response.status_code == 201, response.text
        assert response.json()["comment"] is None
