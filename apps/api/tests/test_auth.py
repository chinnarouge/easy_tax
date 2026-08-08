from fastapi.testclient import TestClient

from apps.api.app.main import app

client = TestClient(app)


def test_register_and_login() -> None:
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "secret123", "full_name": "Test User"},
    )
    assert reg.status_code == 200
    token = reg.json()["token"]
    assert token

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "test@example.com"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "secret123"},
    )
    assert login.status_code == 200
    assert login.json()["token"]


def test_login_wrong_password() -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "wrong@example.com", "password": "correct", "full_name": "X"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "incorrect"},
    )
    assert response.status_code == 401


def test_me_without_token() -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_duplicate_register() -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "pass123", "full_name": "Dup"},
    )
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "pass456", "full_name": "Dup2"},
    )
    assert response.status_code == 409
