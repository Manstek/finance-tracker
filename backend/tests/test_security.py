"""Негативные проверки безопасности (NFR-1, NFR-2, задача #27).

- SQL-инъекции: все запросы строятся SQLAlchemy с параметризацией; инъекция
  в данных должна сохраняться как литерал, не меняя поведение.
- XSS: API отдаёт только JSON; экранирование выполняет фронтенд (escapeHtml).
- Токены: срок жизни ограничен (30 минут, NFR-1), истёкший токен → 401.
"""

from datetime import date, datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import create_access_token
from app.main import app

PASSWORD = "local-test-password"
INJECTION_PAYLOADS = [
    "'; DROP TABLE users; --",
    "1' OR '1'='1",
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
]


def account(client: TestClient, name: str) -> dict[str, str]:
    data = {"username": name, "password": PASSWORD}
    response = client.post("/api/v1/auth/register", json=data)
    assert response.status_code == 201, response.text
    login = client.post("/api/v1/auth/login", json=data)
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_security_headers():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"


def test_username_pattern_blocks_injection():
    """Инъекция в username отсекается валидацией (422), а не доходит до БД."""
    with TestClient(app) as client:
        for name in ("admin'--", "ivan OR 1=1", "user; DROP TABLE users;"):
            response = client.post(
                "/api/v1/auth/register", json={"username": name, "password": PASSWORD}
            )
            assert response.status_code == 422, response.text


def test_injection_payloads_stored_as_literal():
    """Инъекция в данных операции сохраняется как литерал и не меняет поведение."""
    with TestClient(app) as client:
        headers = account(client, "injection_user")
        today = date.today().isoformat()
        for index, payload in enumerate(INJECTION_PAYLOADS):
            response = client.post(
                "/api/v1/operations",
                headers=headers,
                json={"type": "expense", "amount": 10 + index, "date": today, "comment": payload},
            )
            assert response.status_code == 201, response.text
            assert response.json()["comment"] == payload  # литерал, без интерпретации

        # Таблица users на месте, данные не потеряны
        listing = client.get("/api/v1/operations", headers=headers).json()
        assert listing["total"] == len(INJECTION_PAYLOADS)
        assert {item["comment"] for item in listing["items"]} == set(INJECTION_PAYLOADS)

        # Вход по-прежнему работает — «DROP TABLE» ничего не сделал
        assert client.post(
            "/api/v1/auth/login", json={"username": "injection_user", "password": PASSWORD}
        ).status_code == 200


def test_token_lifetime():
    """expires_in совпадает с настройками; истёкший токен → 401 (NFR-1)."""
    settings = get_settings()
    with TestClient(app) as client:
        account(client, "token_lifetime")
        login = client.post(
            "/api/v1/auth/login", json={"username": "token_lifetime", "password": PASSWORD}
        )
        token = login.json()
        assert token["expires_in"] == settings.access_token_expire_minutes * 60
        assert client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token['access_token']}"}
        ).status_code == 200

        # Токен с истёкшим сроком, подписанный тем же секретом, отклоняется
        expired = jwt.encode(
            {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
        assert response.status_code == 401, response.text
