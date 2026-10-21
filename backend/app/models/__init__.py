"""
Models package — import all ORM models so Alembic can discover them.
"""

from app.models.institution import InstitutionRecord  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401
from app.models.application import Application, ApplicationStatus, ApplicationType  # noqa: F401
from app.models.document import Document, DocumentType, OCRStatus  # noqa: F401
from app.models.validation import (  # noqa: F401
    ValidationRun,
    ValidationFinding,
    RunStatus,
    FindingSeverity,
    FindingStatus,
)
from app.models.anomaly import AnomalyFlag  # noqa: F401
from app.models.verification import VerificationResult, VerificationStatus  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.alert import ApplicationAlert  # noqa: F401

__all__ = [
    "InstitutionRecord",
    "User",
    "UserRole",
    "Application",
    "ApplicationStatus",
    "ApplicationType",
    "Document",
    "DocumentType",
    "OCRStatus",
    "ValidationRun",
    "ValidationFinding",
    "RunStatus",
    "FindingSeverity",
    "FindingStatus",
    "AnomalyFlag",
    "VerificationResult",
    "VerificationStatus",
    "AuditLog",
    "ApplicationAlert",
]
