import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.main import app
from app.models import User


@pytest.mark.parametrize(
    ("username", "new_password", "overlong"),
    [
        ("reset_ascii", "a" * 72, "a" * 73),
        ("reset_utf8", "я" * 36, "я" * 36 + "a"),
    ],
)
def test_admin_reset_and_login(username, new_password, overlong):
    old_password = "old-password-123"
    with TestClient(app) as client:
        def login(name, password):
            return client.post("/api/v1/auth/login", json={"username": name, "password": password})

        admin_name = f"{username}_admin"
        for name in (admin_name, username):
            response = client.post(
                "/api/v1/auth/register", json={"username": name, "password": old_password}
            )
            assert response.status_code == 201, response.text
        user_id = response.json()["id"]
        with SessionLocal.begin() as db:
            db.scalar(select(User).where(User.username == admin_name)).is_admin = True

        response = login(admin_name, old_password)
        assert response.status_code == 200, response.text
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        endpoint = f"/api/v1/admin/users/{user_id}/reset-password"

        for invalid in (overlong, "abcd\0efgh", "short"):
            response = client.post(endpoint, headers=headers, json={"new_password": invalid})
            assert response.status_code == 422, response.text
        assert login(username, old_password).status_code == 200

        response = client.post(endpoint, headers=headers, json={"new_password": new_password})
        assert response.status_code == 200, response.text
        assert login(username, old_password).status_code == 401
        response = login(username, new_password)
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200, response.text
        assert response.json()["id"] == user_id
