from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

UTC = timezone.utc

from app.services import auth_service


class _DummyId:
    def __init__(self, value):
        self.id = value
        self._value = value

    def __str__(self):
        return f"user:{self._value}"


class _FakeDB:
    def __init__(self):
        self.query_responses = []
        self.created = []
        self.queries = []

    def create(self, table, payload):
        self.created.append((table, payload))
        if table == "password_resets":
            return {"id": "password_resets:1"}
        return [{"id": _DummyId("1")}]

    def query(self, statement, variables):
        self.queries.append((statement, variables))
        if self.query_responses:
            return self.query_responses.pop(0)
        return []


def test_create_user_creates_pending_user_and_sends_verification(monkeypatch):
    fake_db = _FakeDB()
    sent = {}
    monkeypatch.setattr(auth_service, "db", fake_db)
    monkeypatch.setattr(auth_service, "hash_password", lambda *_: "hashed")
    monkeypatch.setattr(auth_service, "send_email", lambda to, subject, body: sent.update({"to": to, "subject": subject, "body": body}))
    monkeypatch.setattr(auth_service.secrets, "token_urlsafe", lambda *_: "verify-code")

    user = SimpleNamespace(name="Ana", email="ANA@EXAMPLE.COM", password="p")
    result = auth_service.create_user(user)

    assert result[0]["id"].id == "1"
    assert fake_db.created[0][0] == "user"
    assert fake_db.created[1][0] == "email_verifications"
    assert sent["to"] == "ana@example.com"
    assert "verify-code" in sent["body"]


def test_verify_email_code_success(monkeypatch):
    fake_db = _FakeDB()
    expires = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
    fake_db.query_responses = [[{"expires_at": expires, "user_id": "user:1"}], [], []]
    monkeypatch.setattr(auth_service, "db", fake_db)

    result = auth_service.verify_email_code("code")

    assert result == {"verified": True}
    assert len(fake_db.queries) == 3


def test_authenticate_user_unverified_email_returns_error(monkeypatch):
    fake_db = _FakeDB()
    fake_db.query_responses = [[{"id": _DummyId("1"), "password": "hashed", "email_verified": False}]]
    monkeypatch.setattr(auth_service, "db", fake_db)
    monkeypatch.setattr(auth_service, "verify_password", lambda *_: True)

    result = auth_service.authenticate_user("ana@example.com", "pass")

    assert result == {"error": "email_not_verified"}


def test_authenticate_user_success(monkeypatch):
    fake_db = _FakeDB()
    fake_db.query_responses = [[{"id": _DummyId("1"), "password": "hashed", "email_verified": True}]]
    monkeypatch.setattr(auth_service, "db", fake_db)
    monkeypatch.setattr(auth_service, "verify_password", lambda *_: True)
    monkeypatch.setattr(auth_service, "create_access_token", lambda *_: "access")
    monkeypatch.setattr(auth_service, "create_refresh_token", lambda *_: "refresh")
    monkeypatch.setattr(auth_service, "hash_token", lambda *_: "hashed-refresh")

    result = auth_service.authenticate_user("ana@example.com", "pass")

    assert result["access_token"] == "access"
    assert fake_db.created[-1][0] == "sessions"


def test_refresh_access_token_success(monkeypatch):
    fake_db = _FakeDB()
    fake_db.query_responses = [[{"id": "sessions:1", "revoked": False, "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat()}]]
    monkeypatch.setattr(auth_service, "db", fake_db)
    monkeypatch.setattr(auth_service, "decode_token", lambda *_: {"type": "refresh", "sub": "1"})
    monkeypatch.setattr(auth_service, "hash_token", lambda *_: "hash")
    monkeypatch.setattr(auth_service, "create_access_token", lambda *_: "new-access")
    monkeypatch.setattr(auth_service, "create_refresh_token", lambda *_: "new-refresh")

    result = auth_service.refresh_access_token("old")

    assert result["refresh_token"] == "new-refresh"
    assert fake_db.created[-1][0] == "sessions"


def test_logout_user_revokes_session(monkeypatch):
    fake_db = _FakeDB()
    fake_db.query_responses = [[{"id": "sessions:1"}], []]
    monkeypatch.setattr(auth_service, "db", fake_db)
    monkeypatch.setattr(auth_service, "hash_token", lambda *_: "hash")

    result = auth_service.logout_user("refresh")

    assert result["success"] is True
    assert "UPDATE type::record" in fake_db.queries[-1][0]


def test_reset_pass_request_existing_user_sends_email(monkeypatch):
    fake_db = _FakeDB()
    fake_db.query_responses = [[{"id": _DummyId("1")}]]
    sent = {}
    monkeypatch.setattr(auth_service, "db", fake_db)
    monkeypatch.setattr(auth_service, "send_email", lambda to, subject, body: sent.update({"to": to, "subject": subject, "body": body}))
    monkeypatch.setattr(auth_service.secrets, "token_urlsafe", lambda *_: "reset-code")

    result = auth_service.reset_pass_request(SimpleNamespace(email="ana@example.com"))

    assert result["success"] is True
    assert fake_db.created[-1][0] == "password_resets"
    assert sent["to"] == "ana@example.com"
    assert "reset-code" in sent["body"]


def test_verify_reset_pass_code_invalid_when_used(monkeypatch):
    fake_db = _FakeDB()
    fake_db.query_responses = [[{"used": True, "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(), "user_id": "user:1"}]]
    monkeypatch.setattr(auth_service, "db", fake_db)

    result = auth_service.verify_reset_pass_code("code")

    assert result is None


def test_reset_pass_rejects_mismatched_passwords(monkeypatch):
    result = auth_service.reset_pass(SimpleNamespace(code="x", password="a", confirmPass="b"))
    assert result["success"] is False
    assert result["message"] == "Passwords do not match"


def test_reset_pass_success(monkeypatch):
    fake_db = _FakeDB()
    fake_db.query_responses = [[{
        "id": "password_resets:1",
        "used": False,
        "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
        "user_id": "user:1",
    }], [], []]
    monkeypatch.setattr(auth_service, "db", fake_db)
    monkeypatch.setattr(auth_service, "hash_password", lambda *_: "hashed-new")

    result = auth_service.reset_pass(SimpleNamespace(code="x", password="newpass", confirmPass="newpass"))

    assert result["success"] is True
    assert result["message"] == "Password reset successfully"
