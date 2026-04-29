from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
import httpx

from auth import get_current_user
from config import settings
from models.misc import UserCreate, UserLogin, RefreshTokenRequest, ResetPasswordRequest, ResetPassword, LogoutRequest

router = APIRouter()
AUTH_API_BASE = f"{settings.AUTH_API_BASE}/auth"


async def _proxy(method: str, endpoint: str, json_data: dict = None, params: dict = None):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method,
                f"{AUTH_API_BASE}{endpoint}",
                json=json_data,
                params=params,
                timeout=10.0,
            )
            return JSONResponse(status_code=response.status_code, content=response.json())
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Auth service unavailable: {exc}")
        except Exception:
            raise HTTPException(status_code=500, detail="Internal server error parsing auth response")


@router.post("/register", status_code=201)
@router.post("/signup", status_code=201)
async def register(user: UserCreate):
    return await _proxy("POST", "/signup", json_data=user.model_dump())


@router.post("/login")
async def login(credentials: UserLogin):
    return await _proxy("POST", "/login", json_data=credentials.model_dump())


@router.post("/refresh")
async def refresh_token(payload: RefreshTokenRequest):
    return await _proxy("POST", "/refresh", json_data=payload.model_dump())


@router.get("/verify-email")
async def verify_email(code: str = Query(..., min_length=8)):
    return await _proxy("GET", "/verify-email", params={"code": code})


@router.post("/reset-password/request")
async def reset_pass_request(request: ResetPasswordRequest):
    return await _proxy("POST", "/reset-password/request", json_data=request.model_dump())


@router.get("/reset-password/verify")
async def verify_reset_password(code: str = Query(..., min_length=8)):
    return await _proxy("GET", "/reset-password/verify", params={"code": code})


@router.post("/reset-password/confirm")
async def reset_password(request: ResetPassword):
    return await _proxy("POST", "/reset-password/confirm", json_data=request.model_dump())


@router.post("/logout")
async def logout(request: LogoutRequest):
    return await _proxy("POST", "/logout", json_data=request.model_dump())


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    user = dict(current_user)
    user.pop("password", None)
    user.pop("password_hash", None)
    return user
