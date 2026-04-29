from fastapi.testclient import TestClient

from app.main import app
from app.routers import auth_router


def _build_client(monkeypatch):
    monkeypatch.setattr("app.main.connect", lambda: None)
    return TestClient(app)


def test_signup_returns_created_user(monkeypatch):
    client = _build_client(monkeypatch)
    monkeypatch.setattr(auth_router, "create_user", lambda user: {"id": "user:1", "email": user.email})

    response = client.post("/auth/signup", json={"name": "Ana", "email": "ana@example.com", "password": "P@ss1234"})

    assert response.status_code == 200
    assert response.json()["id"] == "user:1"


def test_login_invalid_credentials(monkeypatch):
    client = _build_client(monkeypatch)
    monkeypatch.setattr(auth_router, "authenticate_user", lambda *_: None)

    response = client.post("/auth/login", json={"email": "ana@example.com", "password": "bad"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_unverified_email_returns_403(monkeypatch):
    client = _build_client(monkeypatch)
    monkeypatch.setattr(auth_router, "authenticate_user", lambda *_: {"error": "email_not_verified"})

    response = client.post("/auth/login", json={"email": "ana@example.com", "password": "ok"})

    assert response.status_code == 403
    assert "verify your email" in response.json()["detail"].lower()


def test_login_success(monkeypatch):
    client = _build_client(monkeypatch)
    monkeypatch.setattr(
        auth_router,
        "authenticate_user",
        lambda *_: {"access_token": "a", "refresh_token": "r", "token_type": "bearer"},
    )

    response = client.post("/auth/login", json={"email": "ana@example.com", "password": "ok"})

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_refresh_invalid_token(monkeypatch):
    client = _build_client(monkeypatch)
    monkeypatch.setattr(auth_router, "refresh_access_token", lambda *_: None)

    response = client.post("/auth/refresh", json={"refresh_token": "bad"})

    assert response.status_code == 401


def test_verify_email_invalid_code(monkeypatch):
    client = _build_client(monkeypatch)
    monkeypatch.setattr(auth_router, "verify_email_code", lambda *_: None)

    response = client.get("/auth/verify-email", params={"code": "abcdefgh"})

    assert response.status_code == 400


def test_reset_password_request_success(monkeypatch):
    client = _build_client(monkeypatch)
    monkeypatch.setattr(auth_router, "reset_pass_request", lambda *_: {"success": True})

    response = client.post("/auth/reset-password/request", json={"email": "ana@example.com"})

    assert response.status_code == 200
    assert "password reset link has been sent" in response.json()["message"].lower()


def test_verify_reset_password_invalid(monkeypatch):
    client = _build_client(monkeypatch)
    monkeypatch.setattr(auth_router, "verify_reset_pass_code", lambda *_: None)

    response = client.get("/auth/reset-password/verify", params={"code": "abcdefgh"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired reset link"


def test_reset_password_confirm_mismatch(monkeypatch):
    client = _build_client(monkeypatch)
    monkeypatch.setattr(auth_router, "reset_pass", lambda *_: {"success": False, "message": "Passwords do not match"})

    response = client.post(
        "/auth/reset-password/confirm",
        json={"code": "abcdefgh", "password": "Pass1", "confirmPass": "Pass2"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Passwords do not match"


def test_logout_failure(monkeypatch):
    client = _build_client(monkeypatch)
    monkeypatch.setattr(auth_router, "logout_user", lambda *_: {"success": False})

    response = client.post("/auth/logout", json={"refresh_token": "r"})

    assert response.status_code == 400


def test_logout_success(monkeypatch):
    client = _build_client(monkeypatch)
    monkeypatch.setattr(auth_router, "logout_user", lambda *_: {"success": True})

    response = client.post("/auth/logout", json={"refresh_token": "r"})

    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"
