from datetime import datetime, timedelta, timezone
import secrets
from jose import JWTError

UTC = timezone.utc


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_dt(s: str) -> datetime:
    """Parse an ISO datetime string into a timezone-aware UTC datetime."""
    dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)

from app.db.surreal import db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    REFRESH_TOKEN_EXPIRE_HOURS,
)
from app.core import config
from app.services.email_service import send_email


def create_user(user):
    hashed = hash_password(user.password)
    now = _now()

    result = db.create("user", {
        "name": user.name,
        "email": user.email.strip().lower(),
        "password": hashed,
        "status": "pending",
        "email_verified": False,
        "date_joined": now.isoformat(),
        "updated_at": now.isoformat(),
    })

    created_user = result[0] if isinstance(result, list) and result else result
    user_id = created_user["id"].id if created_user and "id" in created_user else None

    if user_id:
        _create_and_send_email_verification(user.email.strip().lower(), user_id)

    return result


def _create_and_send_email_verification(email: str, user_id: str) -> None:
    now = _now()
    expires_at = now + timedelta(seconds=config.EMAIL_VERIFICATION_TTL_SECONDS)
    code = secrets.token_urlsafe(32)

    db.create("email_verifications", {
        "code": code,
        "user_id": user_id,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
    })

    verify_url = f"{config.APP_BASE_URL.rstrip('/')}/auth/verify-email?code={code}"
    subject = "Verify your email"
    body = f"Click the link to verify your email:\n\n{verify_url}\n\nThis link expires at {expires_at.isoformat()} UTC."
    send_email(email, subject, body)


def verify_email_code(code: str):
    rows = db.query(
        "SELECT * FROM email_verifications WHERE code = $code LIMIT 1",
        {"code": code},
    )

    if not rows:
        return None

    record = rows[0]
    expires_at = record.get("expires_at")
    user_id = record.get("user_id")

    if not expires_at or not user_id:
        return None

    try:
        expires_dt = _parse_dt(expires_at)
    except Exception:
        return None

    if _now() > expires_dt:
        return None

    now = _now().isoformat()
    db.query(
    "UPDATE type::record($table, $id) SET email_verified = true, status = 'active', updated_at = $now",
    {
        "table": "user",
        "id": str(user_id).split(":")[-1],
        "now": now,
    },
)
    db.query("DELETE FROM email_verifications WHERE code = $code", {"code": code})

    return {"verified": True}


def authenticate_user(email: str, password: str):
    users = db.query(
        "SELECT * FROM user WHERE email = $email",
        {"email":email.strip().lower()}
    )

    if not users:
        return None
    
    user = users[0]

    if not verify_password(password, user["password"]):
        return None

    if not user.get("email_verified"):
        return {"error": "email_not_verified"}

    user_id = user["id"].id
    access_token = create_access_token({"sub": user_id})
    refresh_token = create_refresh_token({"sub": user_id})

    db.create("sessions", {
        "user_id": user_id,
        "refresh_token_hash": hash_token(refresh_token),
        "expires_at": (_now() + timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS)).isoformat(),
        "created_at": _now().isoformat(),
        "revoked": False,
    })

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def refresh_access_token(old_refresh_token: str):
    try:
        payload = decode_token(old_refresh_token)

        if payload.get("type") != "refresh":
            return None

        user_id = payload.get("sub")
        hashed = hash_token(old_refresh_token)

        # find session
        sessions = db.query(
            "SELECT * FROM sessions WHERE refresh_token_hash = $hash LIMIT 1",
            {"hash": hashed}
        )

        if not sessions or not sessions[0]:
            return None

        session = sessions[0]

        if session.get("revoked"):
            return None

        expires = _parse_dt(session["expires_at"])
        if _now() > expires:
            return None

        session_id = str(session["id"])
        session_table, session_record_id = session_id.split(":", 1)
        db.query(
            "UPDATE type::record($table, $id) SET revoked = true",
            {"table": session_table, "id": session_record_id}
        )

        new_access = create_access_token({"sub": user_id})
        new_refresh = create_refresh_token({"sub": user_id})

        db.create("sessions", {
            "user_id": user_id,
            "refresh_token_hash": hash_token(new_refresh),
            "expires_at": (_now() + timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS)).isoformat(),
            "created_at": _now().isoformat(),
            "revoked": False
        })

        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
        }

    except (JWTError, ValueError, KeyError, TypeError):
        return None
    
def logout_user(refresh_token: str):
    if not refresh_token:
        return {"success": False, "message": "Missing refresh token"}

    hashed = hash_token(refresh_token)

    sessions = db.query(
        "SELECT * FROM sessions WHERE refresh_token_hash = $hash LIMIT 1",
        {"hash": hashed},
    )

    if not sessions or not sessions[0]:
        return {"success": True}

    session = sessions[0]

    session_id = str(session["id"])
    session_table, session_record_id = session_id.split(":", 1)
    db.query(
        "UPDATE type::record($table, $id) SET revoked = true",
        {"table": session_table, "id": session_record_id},
    )

    return {"success": True}


def reset_pass_request(request):
    normalized_email = request.email.strip().lower()
    users = db.query(
        "SELECT * FROM user WHERE email = $email LIMIT 1",
        {"email": normalized_email},
    )

    # Return success even when user is missing to avoid email enumeration.
    if not users:
        return {"success": True}

    user = users[0]
    user_id = user["id"].id if hasattr(user.get("id"), "id") else str(user.get("id")).split(":")[-1]

    now = _now()
    expires_at = now + timedelta(seconds=config.PASSWORD_RESET_TTL_SECONDS)
    code = secrets.token_urlsafe(32)

    db.create(
        "password_resets",
        {
            "code": code,
            "user_id": user_id,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "used": False,
        },
    )

    base_path = f"{config.FRONTEND_BASE_URL.rstrip('/')}{config.PASSWORD_RESET_PATH}"
    separator = "&" if "?" in base_path else "?"
    reset_url = f"{base_path}{separator}code={code}"
    subject = "Reset your password"
    body = (
        "Click the link to reset your password:\n\n"
        f"{reset_url}\n\n"
        f"This link expires at {expires_at.isoformat()} UTC."
    )
    send_email(normalized_email, subject, body)
    return {"success": True}


def verify_reset_pass_code(code: str):
    rows = db.query(
        "SELECT * FROM password_resets WHERE code = $code LIMIT 1",
        {"code": code},
    )

    if not rows:
        return None

    record = rows[0]
    if record.get("used"):
        return None

    expires_at = record.get("expires_at")
    user_id = record.get("user_id")
    if not expires_at or not user_id:
        return None

    try:
        expires_dt = _parse_dt(expires_at)
    except Exception:
        return None

    if _now() > expires_dt:
        return None

    return {"valid": True}


def reset_pass(request):
    if request.password != request.confirmPass:
        return {"success": False, "message": "Passwords do not match"}

    rows = db.query(
        "SELECT * FROM password_resets WHERE code = $code LIMIT 1",
        {"code": request.code},
    )
    if not rows:
        return {"success": False, "message": "Invalid or expired reset code"}

    record = rows[0]
    if record.get("used"):
        return {"success": False, "message": "Invalid or expired reset code"}

    expires_at = record.get("expires_at")
    user_id = record.get("user_id")
    if not expires_at or not user_id:
        return {"success": False, "message": "Invalid or expired reset code"}

    try:
        expires_dt = _parse_dt(expires_at)
    except Exception:
        return {"success": False, "message": "Invalid or expired reset code"}

    if _now() > expires_dt:
        return {"success": False, "message": "Invalid or expired reset code"}

    now = _now().isoformat()
    db.query(
        "UPDATE type::record($table, $id) SET password = $password, updated_at = $now",
        {
            "table": "user",
            "id": str(user_id).split(":")[-1],
            "password": hash_password(request.password),
            "now": now,
        },
    )

    reset_record_id = str(record["id"]).split(":")[-1]
    db.query(
        "UPDATE type::record($table, $id) SET used = true",
        {"table": "password_resets", "id": reset_record_id},
    )

    return {"success": True, "message": "Password reset successfully"}


def get_me(token: str):
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id or payload.get("type") == "refresh":
            return None
    except Exception:
        return None

    users = db.query(
        "SELECT id, name, email, status, email_verified, date_joined, updated_at FROM user WHERE meta::id(id) = $id LIMIT 1",
        {"id": user_id},
    )

    if not users:
        return None

    return users[0]