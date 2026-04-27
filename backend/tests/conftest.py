"""Shared fixtures for all unit tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


ADMIN_USER = {
    "id": "admin1",
    "email": "admin@test.com",
    "role": "admin",
    "is_active": True,
    "name": "Admin User",
    "password_hash": "hashed",
}

REGULAR_USER = {
    "id": "user1",
    "email": "user@test.com",
    "role": "user",
    "is_active": True,
    "name": "Regular User",
    "password_hash": "hashed",
}


class MockDB:
    """In-memory mock for the DB dependency."""

    def __init__(self):
        self.query = AsyncMock(return_value=[])
        self.create = AsyncMock(return_value={})
        self.select_one = AsyncMock(return_value=None)
        self.select_all = AsyncMock(return_value=[])
        self.update = AsyncMock(return_value={})
        self.delete = AsyncMock(return_value=True)
        self.exists = AsyncMock(return_value=False)
        self.count = AsyncMock(return_value=0)

    def reset(self):
        for attr in ("query", "create", "select_one", "select_all", "update", "delete", "exists", "count"):
            getattr(self, attr).reset_mock()
        self.query.return_value = []
        self.create.return_value = {}
        self.select_one.return_value = None
        self.update.return_value = {}
        self.delete.return_value = True
        self.count.return_value = 0


@pytest.fixture
def mock_db():
    return MockDB()


def _make_client(mock_db, overrides: dict):
    from main import app
    from database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db
    for dep, impl in overrides.items():
        app.dependency_overrides[dep] = impl

    with patch("main.connect_db", new_callable=AsyncMock), \
         patch("main.disconnect_db", new_callable=AsyncMock):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture
def client(mock_db):
    """Unauthenticated test client."""
    yield from _make_client(mock_db, {})


@pytest.fixture
def user_client(mock_db):
    """Client with a regular user injected as current user."""
    from auth import get_current_user

    yield from _make_client(mock_db, {get_current_user: lambda: REGULAR_USER})


@pytest.fixture
def admin_client(mock_db):
    """Client with an admin user injected as both current_user and current_admin."""
    from auth import get_current_user, get_current_admin

    yield from _make_client(
        mock_db,
        {
            get_current_user: lambda: ADMIN_USER,
            get_current_admin: lambda: ADMIN_USER,
        },
    )
