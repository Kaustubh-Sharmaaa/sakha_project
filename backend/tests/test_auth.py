"""Unit tests for auth.py pure helpers and async dependencies."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_admin,
    get_current_user,
    hash_password,
    optional_user,
    verify_password,
)


# ── hash_password / verify_password ──────────────────────────────────────────


def test_hash_password_returns_different_string():
    plain = "secret123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert len(hashed) > 20


def test_hash_password_produces_unique_hashes():
    hashed1 = hash_password("same")
    hashed2 = hash_password("same")
    assert hashed1 != hashed2  # bcrypt salts are random


def test_verify_password_correct():
    plain = "mypassword"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("correct")
    assert verify_password("wrong", hashed) is False


def test_verify_password_invalid_hash_returns_false():
    assert verify_password("anything", "notahash") is False


# ── Token creation / decoding ─────────────────────────────────────────────────


def test_create_access_token_decodes_correctly():
    token = create_access_token("user42", {"role": "admin"})
    payload = decode_token(token)
    assert payload["sub"] == "user42"
    assert payload["type"] == "access"
    assert payload["role"] == "admin"


def test_create_refresh_token_decodes_correctly():
    token = create_refresh_token("user99")
    payload = decode_token(token)
    assert payload["sub"] == "user99"
    assert payload["type"] == "refresh"


def test_create_access_token_without_extra():
    token = create_access_token("user1")
    payload = decode_token(token)
    assert payload["sub"] == "user1"
    assert payload["type"] == "access"


def test_decode_token_invalid_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("completely.invalid.token")
    assert exc_info.value.status_code == 401


def test_decode_token_tampered_raises_401():
    token = create_access_token("u1")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(HTTPException) as exc_info:
        decode_token(tampered)
    assert exc_info.value.status_code == 401


# ── get_current_user ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_valid():
    token = create_access_token("user1", {"role": "user"})
    credentials = MagicMock(credentials=token)
    db = MagicMock()
    db.select_one = AsyncMock(return_value={"id": "user1", "role": "user", "is_active": True})

    user = await get_current_user(credentials=credentials, db=db)

    assert user["id"] == "user1"
    db.select_one.assert_called_once_with("user", "user1")


@pytest.mark.asyncio
async def test_get_current_user_no_credentials_raises_401():
    db = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=None, db=db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_refresh_token_type_raises_401():
    token = create_refresh_token("user1")
    credentials = MagicMock(credentials=token)
    db = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=credentials, db=db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_user_not_found_raises_401():
    token = create_access_token("ghost")
    credentials = MagicMock(credentials=token)
    db = MagicMock()
    db.select_one = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=credentials, db=db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_inactive_raises_403():
    token = create_access_token("user1")
    credentials = MagicMock(credentials=token)
    db = MagicMock()
    db.select_one = AsyncMock(return_value={"id": "user1", "role": "user", "is_active": False})

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=credentials, db=db)
    assert exc_info.value.status_code == 403


# ── get_current_admin ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_admin_valid():
    admin = {"id": "admin1", "role": "admin", "is_active": True}
    result = await get_current_admin(current_user=admin)
    assert result["role"] == "admin"


@pytest.mark.asyncio
async def test_get_current_admin_non_admin_raises_403():
    user = {"id": "user1", "role": "user", "is_active": True}
    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(current_user=user)
    assert exc_info.value.status_code == 403


# ── optional_user ─────────────────────────────────────────────────────────────


def test_optional_user_valid_token():
    token = create_access_token("user1")
    credentials = MagicMock(credentials=token)
    result = optional_user(credentials=credentials)
    assert result == "user1"


def test_optional_user_no_credentials():
    result = optional_user(credentials=None)
    assert result is None


def test_optional_user_invalid_token_returns_none():
    credentials = MagicMock(credentials="bad.token.here")
    result = optional_user(credentials=credentials)
    assert result is None
