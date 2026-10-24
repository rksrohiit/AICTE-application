"""
Core application configuration using Pydantic Settings.

Reads from environment variables or a .env file in the project root.
"""

from __future__ import annotations

from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    APP_NAME: str = "AICTE AI Validation Platform"
    VERSION: str = "0.1.0-mvp"
    DEBUG: bool = True

    # ── Security ───────────────────────────────────────────────────────────────
    SECRET_KEY: str = "dev-secret-key-aicte-sih-2024-platform-eoa-validation"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # ── Database ───────────────────────────────────────────────────────────────
    # The production schema uses PostgreSQL UUID/JSONB types and is intentionally
    # not silently downgraded to SQLite.
    DATABASE_URL: str = "postgresql://localhost:5432/aicte_db"

    # ── Redis / Celery ─────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ── MinIO / Object Storage ─────────────────────────────────────────────────
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "aicte-documents"

    # ── External / Mock APIs ───────────────────────────────────────────────────
    MOCK_API_BASE_URL: str = "http://mock-apis:8001"

    # ── CORS ───────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: object) -> List[str]:
        """Accept a comma-separated string or an already-parsed list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return list(v)  # type: ignore[arg-type]

    @property
    def async_database_url(self) -> str:
        """Return the async-compatible database URL."""
        if not self.DATABASE_URL.startswith(("postgresql://", "postgres://")):
            raise ValueError(
                "DATABASE_URL must use PostgreSQL (postgresql:// or postgres://). "
                "SQLite is not supported because the schema uses PostgreSQL UUID/JSONB types."
            )
        return self.DATABASE_URL.replace(
            "postgresql://", "postgresql+asyncpg://"
        ).replace("postgres://", "postgresql+asyncpg://")


settings = Settings()  # type: ignore[call-arg]
