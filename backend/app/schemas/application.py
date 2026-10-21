"""
Pydantic v2 schemas for application-related API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, field_validator

from app.models.application import ApplicationStatus, ApplicationType


class ApplicationCreate(BaseModel):
    """Payload for creating a new EOA application."""

    institution_name: str
    application_type: ApplicationType
    academic_year: str
    programmes: List[Any] = []


class ApplicationResponse(BaseModel):
    """Full representation of an application returned by the API."""

    id: uuid.UUID
    institution_id: uuid.UUID
    institution_name: str
    application_type: ApplicationType
    status: ApplicationStatus
    submitted_at: datetime | None
    academic_year: str
    programmes: List[Any]
    created_at: datetime
    updated_at: datetime

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


class ApplicationListResponse(BaseModel):
    """Paginated list of applications."""

    total: int
    items: List[ApplicationResponse]
