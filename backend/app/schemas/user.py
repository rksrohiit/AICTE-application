"""
Pydantic v2 schemas for user-related API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    """Payload for creating a new institution user account."""

    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: str = Field(..., min_length=2, max_length=255)
    institution_id: uuid.UUID | None = None


class UserLogin(BaseModel):
    """Credentials for authenticating a user."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Public representation of a user account."""

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    institution_id: uuid.UUID | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("id", "institution_id", mode="before")
    @classmethod
    def parse_uuid(cls, v: object) -> uuid.UUID | None:
        if v is None:
            return None
        if isinstance(v, bytes):
            return uuid.UUID(bytes=v)
        if isinstance(v, str):
            return uuid.UUID(v)
        return v  # type: ignore[return-value]


class TokenResponse(BaseModel):
    """JWT token response returned on successful login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
