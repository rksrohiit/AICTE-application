"""
JWT-based security utilities for the AICTE platform.

Provides token creation/verification and password hashing helpers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password* using standard bcrypt."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify that *plain* matches *hashed* using standard bcrypt."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


# ── JWT helpers ─────────────────────────────────────────────────────────────
def create_access_token(
    data: Dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Encode *data* as a signed JWT access token.

    Args:
        data:          Arbitrary payload to embed in the token. Should include
                       a ``"sub"`` key with the subject (usually ``user.email``).
        expires_delta: How long the token remains valid.  Defaults to
                       ``ACCESS_TOKEN_EXPIRE_MINUTES`` from settings.

    Returns:
        A signed JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT access token.

    Args:
        token: The raw JWT string (without the ``Bearer `` prefix).

    Returns:
        The decoded payload as a plain dict.

    Raises:
        :class:`jose.JWTError`: If the token is invalid, expired, or tampered with.
    """
    try:
        payload: Dict[str, Any] = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise
