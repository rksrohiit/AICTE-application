"""
Pydantic v2 schemas for anomaly-related API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class AnomalyFlagResponse(BaseModel):
    """Public representation of an anomaly flag."""

    id: uuid.UUID
    application_id: uuid.UUID
    document_id: uuid.UUID | None
    check_type: str
    severity: str
    confidence: float
    evidence: str | None
    advisory_note: str | None
    created_at: datetime
    is_reviewed: bool
    reviewer_notes: str | None

    model_config = {"from_attributes": True}
