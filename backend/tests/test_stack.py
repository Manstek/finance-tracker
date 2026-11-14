from datetime import date
import subprocess
import sys

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.main import app
from app.models import User


def register(client, username):
    payload = {"username": username, "password": "local-test-password"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    login = client.post("/api/v1/auth/login", json=payload)
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_operations_and_summary():
    with TestClient(app) as client:
        headers = register(client, "stack_operations")
        other_headers = register(client, "stack_other_account")
        endpoint = "/api/v1/operations"
        assert client.get(endpoint).status_code == 401
        for kind, amount in (("income", "150.25"), ("expense", "25.10")):
            result = client.post(
                endpoint, headers=headers,
                json={"type": kind, "amount": amount, "date": date.today().isoformat()},
            )
            assert result.status_code == 201, result.text
            assert result.json()["amount"] == amount
        operation_id = result.json()["id"]
        result = client.get(endpoint, headers=headers, params={"per_page": 1})
        assert result.status_code == 200, result.text
        assert len(result.json()["items"]) == 1
        assert result.json()["total"] == 2
        totals = {"income": "150.25", "expense": "25.10", "balance": "125.15"}
        assert result.json()["totals"] == totals
        assert client.get(f"{endpoint}/summary", headers=headers).json() == totals
        assert client.get(endpoint, headers=other_headers).json()["total"] == 0
        assert client.delete(f"{endpoint}/{operation_id}", headers=other_headers).status_code == 404
        assert client.delete(f"{endpoint}/{operation_id}", headers=headers).status_code == 204
        assert client.get("/api/v1/admin/users", headers=headers).status_code == 403


def test_swagger_authorize_format():
    with TestClient(app) as client:
        register(client, "stack_swagger")
        scheme = client.get("/openapi.json").json()["components"]["securitySchemes"]
        token_url = scheme["OAuth2PasswordBearer"]["flows"]["password"]["tokenUrl"]
        result = client.post(
            token_url,
            data={"grant_type": "password", "username": "stack_swagger", "password": "local-test-password"},
        )
        assert result.status_code == 200, result.text
        headers = {"Authorization": f"Bearer {result.json()['access_token']}"}
        assert client.get("/api/v1/auth/me", headers=headers).json()["username"] == "stack_swagger"
        assert client.post(
            token_url, data={"username": "stack_swagger", "password": "wrong-password"}
        ).status_code == 401


def test_create_admin_password_is_usable():
    password = "я" * 37
    rejected = subprocess.run(
        [sys.executable, "-m", "scripts.create_admin", "stack_cli_admin", "-p", password],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert rejected.returncode == 1, rejected.stdout + rejected.stderr
    assert "72" in rejected.stdout
    with SessionLocal() as db:
        assert db.scalar(select(User.id).where(User.username == "stack_cli_admin")) is None
    password = "я" * 36
    subprocess.run(
        [sys.executable, "-m", "scripts.create_admin", "stack_cli_admin", "-p", password],
        check=True,
    )
    with TestClient(app) as client:
        result = client.post(
            "/api/v1/auth/login", json={"username": "stack_cli_admin", "password": password}
        )
        assert result.status_code == 200, f"CLI created admin, login returned {result.status_code}"
        headers = {"Authorization": f"Bearer {result.json()['access_token']}"}
        assert client.get("/api/v1/auth/me", headers=headers).json()["is_admin"] is True
