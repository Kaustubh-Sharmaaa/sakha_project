from fastapi import APIRouter, HTTPException, Query, Header
from app.schemas.user import UserCreate, UserLogin, RefreshTokenRequest, ResetPasswordRequest, ResetPassword
from app.services.auth_service import create_user, authenticate_user, verify_email_code, refresh_access_token, logout_user, reset_pass_request, verify_reset_pass_code, reset_pass, get_me
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

class LogoutRequest(BaseModel):
    refresh_token: str


@router.post("/signup")
@router.post("/register")
def signup(user: UserCreate):
    return create_user(user)


@router.post("/login")
def login(user: UserLogin):
    result = authenticate_user(user.email, user.password)

    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if isinstance(result, dict) and result.get("error") == "email_not_verified":
        raise HTTPException(status_code=403, detail="Please verify your email before signing in")

    return result


@router.post("/refresh")
def refresh_token(payload: RefreshTokenRequest):
    token = refresh_access_token(payload.refresh_token)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    return token


@router.get("/verify-email")
def verify_email(code: str = Query(..., min_length=8)):
    result = verify_email_code(code)
    if not result:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    return result

@router.post("/reset-password/request")
def reset_pass_request_endpoint(request: ResetPasswordRequest):
    result = reset_pass_request(request)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail="Could not send a password reset link")

    return {"message": "If your email exists, a password reset link has been sent"}


@router.get("/reset-password/verify")
def verify_reset_password(code: str = Query(..., min_length=8)):
    result = verify_reset_pass_code(code)
    if not result:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    return result


@router.post("/reset-password/confirm")
def reset_password(request: ResetPassword):
    result = reset_pass(request)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "There was an error resetting your password"))
    return result

@router.post("/logout")
def logout(request: LogoutRequest):
    result = logout_user(request.refresh_token)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail="Logout failed")

    return {"message": "Logged out successfully"}


@router.get("/me")
def me(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[len("Bearer "):]
    user = get_me(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user