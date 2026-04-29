import os
from dotenv import load_dotenv

load_dotenv()

def _get_env(key: str, default: str | None = None) -> str | None:
    val = os.getenv(key)
    if val is None:
        return default
    val = val.strip()
    return val if val != "" else default


APP_BASE_URL = _get_env("APP_BASE_URL", "http://localhost:8001")

# JWT
SECRET_KEY = _get_env("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
ALGORITHM = _get_env("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(_get_env("ACCESS_TOKEN_EXPIRE_MINUTES", "15") or "15")
REFRESH_TOKEN_EXPIRE_HOURS = int(_get_env("REFRESH_TOKEN_EXPIRE_HOURS", "24") or "24")

SMTP_HOST = _get_env("SMTP_HOST")
SMTP_PORT = int(_get_env("SMTP_PORT", "587") or "587")
SMTP_USER = _get_env("SMTP_USER")
SMTP_PASSWORD = _get_env("SMTP_PASSWORD")
SMTP_FROM = _get_env("SMTP_FROM", SMTP_USER or "")
SMTP_USE_TLS = (_get_env("SMTP_USE_TLS", "true") or "true").lower() in {"1", "true", "yes", "y"}
SMTP_USE_SSL = (_get_env("SMTP_USE_SSL", "false") or "false").lower() in {"1", "true", "yes", "y"}

SURREAL_URL = _get_env("SURREAL_URL")
SURREAL_NAMESPACE = _get_env("SURREAL_NAMESPACE")
SURREAL_DB = _get_env("SURREAL_DB")
SURREAL_USERNAME = _get_env("SURREAL_USERNAME")
SURREAL_PASSWORD = _get_env("SURREAL_PASSWORD")

# Seconds
EMAIL_VERIFICATION_TTL_SECONDS = int(_get_env("EMAIL_VERIFICATION_TTL_SECONDS", "3600") or "3600")
PASSWORD_RESET_TTL_SECONDS = int(_get_env("PASSWORD_RESET_TTL_SECONDS", "1800") or "1800")
FRONTEND_BASE_URL = _get_env("FRONTEND_BASE_URL", "http://localhost:5173")
PASSWORD_RESET_PATH = _get_env("PASSWORD_RESET_PATH", "/reset-password")

