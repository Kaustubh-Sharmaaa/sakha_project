"""
config.py — centralised settings for the Sakha Product API.

All values can be overridden via environment variables or a .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── SurrealDB ──────────────────────────────────────────────
    SURREAL_URL: str = "ws://localhost:8000"
    SURREAL_USER: str = "root"
    SURREAL_PASS: str = "root"
    SURREAL_NS: str = "sakha"
    SURREAL_DB: str = "products"

    # ── JWT ────────────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_OPENSSL_RAND"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── File storage ───────────────────────────────────────────
    MEDIA_DIR: str = "media"          # local disk; swap for S3 in storage.py
    MAX_UPLOAD_MB: int = 20

    # ── App ────────────────────────────────────────────────────
    APP_NAME: str = "Sakha Product API"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = ["*"]   # tighten in production

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
