"""
SQLAlchemy 2.0 async database engine, session factory and Base setup.

All database-dependent modules should import ``engine``, ``AsyncSessionLocal``,
``Base``, and ``get_db`` from here.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ── Engine ──────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.async_database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
    future=True,
)

# ── Session factory ─────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Declarative base ────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy ORM models."""


# ── Dependency ──────────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an :class:`AsyncSession`.

    Automatically commits on success and rolls back on exception, then closes
    the session.

    Yields:
        An open :class:`~sqlalchemy.ext.asyncio.AsyncSession`.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
