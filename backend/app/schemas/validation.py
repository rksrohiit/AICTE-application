"""
Pydantic v2 schemas for validation-related API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel

from app.models.validation import FindingSeverity, FindingStatus, RunStatus
from app.schemas.application import ApplicationResponse
from app.schemas.document import DocumentResponse
from app.schemas.anomaly import AnomalyFlagResponse


class ValidationFindingResponse(BaseModel):
    """A single rule evaluation result."""

    id: uuid.UUID
    validation_run_id: uuid.UUID
    rule_id: str
    rule_name: str
    severity: FindingSeverity
    status: FindingStatus
    document_id: uuid.UUID | None
    evidence: str | None
    message: str
    category: str

    model_config = {"from_attributes": True}


class ValidationRunResponse(BaseModel):
    """Summary of a validation run."""

    id: uuid.UUID
    application_id: uuid.UUID
    started_at: datetime
    completed_at: datetime | None
    overall_score: int
    status: RunStatus
    rules_version: str
    findings_count_high: int
    findings_count_medium: int
    findings_count_low: int

    model_config = {"from_attributes": True}


class ValidationReportResponse(BaseModel):
    """Comprehensive validation report combining run metadata and all findings."""

    application: ApplicationResponse
    documents: List[DocumentResponse]
    alerts: List[Dict[str, Any]]
    run: ValidationRunResponse
    validation_run: ValidationRunResponse | None = None
    findings: List[ValidationFindingResponse]
    summary: Dict[str, Any]
    anomalies: List[AnomalyFlagResponse] = []
    verifications: List[Dict[str, Any]] = []
