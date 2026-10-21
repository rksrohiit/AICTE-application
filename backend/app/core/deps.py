"""
FastAPI dependency helpers: current-user resolution and role-based guards.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve and return the authenticated :class:`User` from the JWT token.

    Args:
        token: The raw Bearer JWT extracted by :class:`OAuth2PasswordBearer`.
        db:    An open async database session.

    Returns:
        The :class:`User` ORM instance corresponding to the token subject.

    Raises:
        :class:`~fastapi.HTTPException` 401: If the token is invalid or the
            user no longer exists.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = verify_token(token)
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


async def require_officer(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the current user has OFFICER or SENIOR_OFFICER role.

    Args:
        current_user: The resolved authenticated user.

    Returns:
        The same :class:`User` if the role check passes.

    Raises:
        :class:`~fastapi.HTTPException` 403: If the user is not an officer.
    """
    if current_user.role not in (UserRole.OFFICER, UserRole.SENIOR_OFFICER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Officer or Senior Officer role required.",
        )
    return current_user


async def require_institution(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the current user has the INSTITUTION role.

    Args:
        current_user: The resolved authenticated user.

    Returns:
        The same :class:`User` if the role check passes.

    Raises:
        :class:`~fastapi.HTTPException` 403: If the user is not from an institution.
    """
    if current_user.role != UserRole.INSTITUTION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Institution role required.",
        )
    return current_user
