import os
import subprocess
import sys
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app


def account(client, name):
    data = {"username": name, "password": "local-test-password"}
    response = client.post("/api/v1/auth/register", json=data)
    assert response.status_code == 201, response.text
    identity = response.json()["id"]
    login = client.post("/api/v1/auth/login", json=data)
    assert login.status_code == 200, login.text
    return identity, {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_edit_and_filters():
    with TestClient(app) as client:
        _, owner = account(client, "edit_owner")
        _, other = account(client, "edit_other")
        categories = client.get("/api/v1/categories", headers=owner).json()
        other_categories = client.get("/api/v1/categories", headers=other).json()
        assert len(categories) == len(other_categories) == 6
        assert {c["id"] for c in categories}.isdisjoint(c["id"] for c in other_categories)
        today = date.today().isoformat()
        endpoint = "/api/v1/operations"
        response = client.post(endpoint, headers=owner, json={
            "type": "income", "amount": "100.00", "category_id": categories[0]["id"], "date": today,
        })
        assert response.status_code == 201, response.text
        item = f"{endpoint}/{response.json()['id']}"
        for headers, payload, expected in [
            (other, {"amount": "85.50"}, 404),
            (owner, {"amount": None}, 422),
            (owner, {"amount": "0"}, 422),
            (owner, {"date": (date.today() + timedelta(days=1)).isoformat()}, 400),
            (owner, {"category_id": other_categories[0]["id"]}, 404),
        ]:
            assert client.patch(item, headers=headers, json=payload).status_code == expected
        response = client.patch(item, headers=owner, json={"amount": "85.50", "comment": "updated"})
        assert response.status_code == 200, response.text
        assert response.json()["date"] == today
        assert response.json()["category_id"] == categories[0]["id"]
        result = client.get(endpoint, headers=owner, params={
            "date_from": today, "date_to": today, "type": "income", "category_id": categories[0]["id"],
        }).json()
        assert result["total"] == 1
        assert result["items"][0]["comment"] == "updated"
        assert result["totals"]["balance"] == "85.50"
        assert client.get(endpoint, headers=owner, params={"type": "expense"}).json()["total"] == 0
        assert client.get(endpoint, headers=other).json()["total"] == 0
        assert client.patch(item, headers=owner, json={"category_id": None}).json()["category_id"] is None
        assert client.delete(item, headers=owner).status_code == 204


@pytest.mark.parametrize("endpoint", ["/api/v1/operations", "/api/v1/operations/summary"])
def test_operation_period_validation(endpoint):
    with TestClient(app) as client:
        _, headers = account(client, "period_validation")
        today = date.today()
        earlier = today - timedelta(days=1)
        reversed_period = {"date_from": today.isoformat(), "date_to": earlier.isoformat()}
        response = client.get(endpoint, headers=headers, params=reversed_period)
        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Начало периода (date_from) должно быть не позже окончания (date_to)"
        )

        for field in ("date_from", "date_to"):
            response = client.get(endpoint, headers=headers, params={field: "2026-02-30"})
            assert response.status_code == 422
            error = response.json()["detail"][0]
            assert error["loc"] == ["query", field]
            assert "ГГГГ-ММ-ДД" in error["msg"]

        for period in (
            {},
            {"date_from": today.isoformat()},
            {"date_to": today.isoformat()},
            {"date_from": today.isoformat(), "date_to": today.isoformat()},
        ):
            assert client.get(endpoint, headers=headers, params=period).status_code == 200


def test_admin_deletion():
    created = subprocess.run(
        [sys.executable, "-m", "scripts.create_admin", "mvp_api_admin", "-p", "local-test-password"],
        env=os.environ, capture_output=True,
    )
    assert created.returncode == 0, created.stderr
    with TestClient(app) as client:
        user_id, user = account(client, "mvp_delete_me")
        login = client.post("/api/v1/auth/login", json={"username": "mvp_api_admin", "password": "local-test-password"})
        admin = {"Authorization": f"Bearer {login.json()['access_token']}"}
        endpoint = f"/api/v1/admin/users/{user_id}"
        assert client.delete(endpoint, headers=user).status_code == 403
        assert client.get(endpoint, headers=admin).status_code == 200
        assert client.delete(endpoint, headers=admin).status_code == 204
        assert client.get(endpoint, headers=admin).status_code == 404
        assert client.get("/api/v1/auth/me", headers=user).status_code == 401
