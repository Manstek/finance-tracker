import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api import auth
from app.core.db import SessionLocal
from app.core.default_categories import DEFAULT_CATEGORIES
from app.main import app
from app.models import Category, User


def test_registration_and_password_boundaries():
    with TestClient(app) as client:
        for username, password in (
            ("ascii_limit", "a" * 72),
            ("unicode_limit", "я" * 36),
        ):
            payload = {"username": username, "password": password}
            response = client.post("/api/v1/auth/register", json=payload)
            assert response.status_code == 201, response.text
            assert client.post("/api/v1/auth/register", json=payload).status_code == 409
            with SessionLocal() as db:
                categories = db.scalars(
                    select(Category.name).where(Category.user_id == response.json()["id"])
                )
                assert set(categories) == set(DEFAULT_CATEGORIES)
            login = client.post("/api/v1/auth/login", json=payload)
            assert login.status_code == 200, login.text
            token = login.json()["access_token"]
            me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert me.json()["username"] == username, me.text
            assert client.post(
                "/api/v1/auth/login", json={**payload, "password": password + "a"}
            ).status_code == 401
        for password in ("a" * 73, "я" * 37, "abcd\0efgh"):
            result = client.post(
                "/api/v1/auth/register", json={"username": "too_long", "password": password}
            )
            assert result.status_code == 422, result.text
        with SessionLocal() as db:
            assert db.scalar(select(User.id).where(User.username == "too_long")) is None


def test_registration_rolls_back_after_category_failure(monkeypatch):
    original_seed = auth.seed_default_categories

    def seed_with_duplicate(db, user_id):
        original_seed(db, user_id)
        db.add(Category(user_id=user_id, name=DEFAULT_CATEGORIES[0]))

    payload = {"username": "rollback_user", "password": "test-password"}
    with SessionLocal() as db:
        initial_count = db.scalar(select(func.count()).select_from(Category))
        with monkeypatch.context() as patch:
            patch.setattr(auth, "seed_default_categories", seed_with_duplicate)
            with TestClient(app) as client, pytest.raises(IntegrityError):
                client.post("/api/v1/auth/register", json=payload)
        assert db.scalar(select(User.id).where(User.username == payload["username"])) is None
        assert db.scalar(select(func.count()).select_from(Category)) == initial_count
    with TestClient(app) as client:
        assert client.post("/api/v1/auth/register", json=payload).status_code == 201
