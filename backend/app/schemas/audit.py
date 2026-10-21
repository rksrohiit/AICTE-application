"""
Pydantic v2 schemas for audit-log API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    """Public representation of an audit log entry."""

    id: uuid.UUID
    event_id: uuid.UUID
    timestamp: datetime
    actor: str
    action: str
    application_id: uuid.UUID | None
    document_id: uuid.UUID | None
    rule_id: str | None
    evidence_ref: str | None
    result: str | None
    notes: str | None

    model_config = {"from_attributes": True}
