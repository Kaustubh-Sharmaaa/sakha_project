"""Unit tests for /auth routes: proxy endpoints (register, login, refresh) and local /me."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

REGULAR_USER = {"id": "user1", "email": "user@test.com", "role": "user", "is_active": True, "name": "Regular User"}


def _mock_response(status_code: int, body: dict):
    """Build a fake httpx.Response-like object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    return resp


def _patch_proxy(status_code: int, body: dict):
    """Context manager that patches httpx.AsyncClient so _proxy() returns a canned response."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.request = AsyncMock(return_value=_mock_response(status_code, body))
    return patch("routers.auth_router.httpx.AsyncClient", return_value=mock_client)


# ── /auth/register ────────────────────────────────────────────────────────────


def test_register_success(client):
    body = {"access_token": "tok", "refresh_token": "ref", "token_type": "bearer"}
    with _patch_proxy(201, body):
        resp = client.post("/api/v1/auth/register", json={
            "email": "new@test.com",
            "password": "pass1234",
            "name": "New User",
        })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_email_returns_409(client):
    with _patch_proxy(409, {"detail": "Email already registered"}):
        resp = client.post("/api/v1/auth/register", json={
            "email": "taken@test.com",
            "password": "pass1234",
            "name": "User",
        })
    assert resp.status_code == 409


# ── /auth/login ───────────────────────────────────────────────────────────────


def test_login_success(client):
    body = {"access_token": "tok", "refresh_token": "ref", "token_type": "bearer"}
    with _patch_proxy(200, body):
        resp = client.post("/api/v1/auth/login", json={
            "email": "test@test.com",
            "password": "correctpass",
        })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_user_not_found_returns_401(client):
    with _patch_proxy(401, {"detail": "Invalid credentials"}):
        resp = client.post("/api/v1/auth/login", json={
            "email": "ghost@test.com",
            "password": "pass",
        })
    assert resp.status_code == 401


def test_login_wrong_password_returns_401(client):
    with _patch_proxy(401, {"detail": "Invalid credentials"}):
        resp = client.post("/api/v1/auth/login", json={
            "email": "user@test.com",
            "password": "wrong",
        })
    assert resp.status_code == 401


def test_login_inactive_account_returns_403(client):
    with _patch_proxy(403, {"detail": "Account disabled"}):
        resp = client.post("/api/v1/auth/login", json={
            "email": "user@test.com",
            "password": "pass",
        })
    assert resp.status_code == 403


# ── /auth/refresh ─────────────────────────────────────────────────────────────


def test_refresh_token_success(client):
    body = {"access_token": "new_tok", "token_type": "bearer"}
    with _patch_proxy(200, body):
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "sometoken"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_refresh_token_invalid_returns_401(client):
    with _patch_proxy(401, {"detail": "Invalid or expired refresh token"}):
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "bad.token.here"})
    assert resp.status_code == 401


def test_refresh_access_token_as_refresh_returns_401(client):
    with _patch_proxy(401, {"detail": "Invalid token type"}):
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "access.token.here"})
    assert resp.status_code == 401


def test_refresh_user_not_found_returns_401(client):
    with _patch_proxy(401, {"detail": "User not found"}):
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "ghost_token"})
    assert resp.status_code == 401


# ── /auth/me ──────────────────────────────────────────────────────────────────


def test_me_returns_user_without_password_hash(user_client, mock_db):
    resp = user_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert "password_hash" not in data
    assert data["email"] == REGULAR_USER["email"]
