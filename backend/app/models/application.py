"""
Application ORM model representing an EOA (Extension of Approval) submission.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApplicationType(str, enum.Enum):
    """Type of AICTE application being submitted."""

    EOA_RENEWAL = "EOA_RENEWAL"
    EOA_NEW_PROGRAMME = "EOA_NEW_PROGRAMME"


class ApplicationStatus(str, enum.Enum):
    """Life-cycle status of an application."""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_VALIDATION = "UNDER_VALIDATION"
    VALIDATION_COMPLETE = "VALIDATION_COMPLETE"
    UNDER_REVIEW = "UNDER_REVIEW"
    SENT_FOR_RECTIFICATION = "SENT_FOR_RECTIFICATION"
    APPROVED_FOR_PROCESSING = "APPROVED_FOR_PROCESSING"
    ESCALATED = "ESCALATED"
    REJECTED = "REJECTED"


class Application(Base):
    """An EOA application submitted by an institution."""

    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institution_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_name: Mapped[str] = mapped_column(String(512), nullable=False)
    application_type: Mapped[ApplicationType] = mapped_column(
        Enum(ApplicationType, name="applicationtype"), nullable=False
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="applicationstatus"),
        nullable=False,
        default=ApplicationStatus.DRAFT,
        index=True,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    academic_year: Mapped[str] = mapped_column(String(10), nullable=False)
    programmes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────────────────────────
    institution: Mapped["InstitutionRecord"] = relationship(  # noqa: F821
        "InstitutionRecord", back_populates="applications", lazy="select"
    )
    documents: Mapped[list["Document"]] = relationship(  # noqa: F821
        "Document", back_populates="application", lazy="select", cascade="all, delete-orphan"
    )
    validation_runs: Mapped[list["ValidationRun"]] = relationship(  # noqa: F821
        "ValidationRun", back_populates="application", lazy="select", cascade="all, delete-orphan"
    )
    anomaly_flags: Mapped[list["AnomalyFlag"]] = relationship(  # noqa: F821
        "AnomalyFlag", back_populates="application", lazy="select", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["ApplicationAlert"]] = relationship(  # noqa: F821
        "ApplicationAlert", back_populates="application", lazy="select", cascade="all, delete-orphan"
    )
