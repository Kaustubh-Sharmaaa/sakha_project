"""routers/auth_router.py — register, login, refresh, me."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from database import DB, get_db
from models.misc import RefreshRequest, TokenResponse, UserLogin, UserRegister

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: UserRegister, db: DB = Depends(get_db)):
    existing = await db.query(
        "SELECT id FROM user WHERE email = $email LIMIT 1", {"email": data.email}
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    now = datetime.now(timezone.utc).isoformat()
    record = await db.create(
        "user",
        {
            "email": data.email,
            "password_hash": hash_password(data.password),
            "name": data.name,
            "role": data.role,
            "is_active": True,
            "created_at": now,
        },
    )
    uid = record["id"]
    return {
        "access_token": create_access_token(uid, {"role": data.role}),
        "refresh_token": create_refresh_token(uid),
        "token_type": "bearer",
    }


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: DB = Depends(get_db)):
    rows = await db.query(
        "SELECT * FROM user WHERE email = $email LIMIT 1", {"email": data.email}
    )
    if not rows:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user = rows[0]
    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account disabled")

    uid = user["id"].split(":")[-1] if ":" in str(user["id"]) else str(user["id"])
    return {
        "access_token": create_access_token(uid, {"role": user.get("role", "user")}),
        "refresh_token": create_refresh_token(uid),
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshRequest, db: DB = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    uid = payload["sub"]
    user = await db.select_one("user", uid)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {
        "access_token": create_access_token(uid, {"role": user.get("role", "user")}),
        "refresh_token": create_refresh_token(uid),
        "token_type": "bearer",
    }


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    user = dict(current_user)
    user.pop("password_hash", None)
    return user
