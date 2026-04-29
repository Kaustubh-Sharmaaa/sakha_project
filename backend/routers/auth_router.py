from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)
from database import DB, get_db
from models.misc import UserCreate, UserLogin, RefreshTokenRequest

router = APIRouter()


@router.post("/register", status_code=201)
@router.post("/signup", status_code=201)
async def register(user: UserCreate, db: DB = Depends(get_db)):
    existing = await db.query(
        "SELECT id FROM user WHERE email = $email", {"email": user.email}
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    new_user = await db.create("user", {
        "name": user.name,
        "email": user.email,
        "password_hash": hash_password(user.password),
        "role": "user",
        "is_active": True,
    })
    user_id = new_user.get("id", "")
    return JSONResponse(
        status_code=201,
        content={
            "access_token": create_access_token(user_id),
            "refresh_token": create_refresh_token(user_id),
            "token_type": "bearer",
        },
    )


@router.post("/login")
async def login(credentials: UserLogin, db: DB = Depends(get_db)):
    users = await db.query(
        "SELECT * FROM user WHERE email = $email", {"email": credentials.email}
    )
    if not users:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user = users[0]
    if not verify_password(credentials.password, user.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if user.get("is_active") is False:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    user_id = user.get("id", "")
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh_token(payload: RefreshTokenRequest, db: DB = Depends(get_db)):
    token_data = decode_token(payload.refresh_token)
    if token_data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id: str = token_data["sub"]
    user = await db.select_one("user", user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return {
        "access_token": create_access_token(user_id),
        "token_type": "bearer",
    }


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    user = dict(current_user)
    user.pop("password", None)
    user.pop("password_hash", None)
    return user
