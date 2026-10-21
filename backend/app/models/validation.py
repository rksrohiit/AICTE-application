"""
Validation ORM models: ValidationRun and ValidationFinding.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RunStatus(str, enum.Enum):
    """Lifecycle status of a validation run."""

    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class FindingSeverity(str, enum.Enum):
    """Severity level of an individual validation finding."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FindingStatus(str, enum.Enum):
    """Outcome of an individual validation rule evaluation."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIPPED = "SKIPPED"


class ValidationRun(Base):
    """A complete validation cycle triggered for one application."""

    __tablename__ = "validation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="runstatus"), nullable=False, default=RunStatus.RUNNING
    )
    rules_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    findings_count_high: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    findings_count_medium: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    findings_count_low: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Relationships ────────────────────────────────────────────────────────
    application: Mapped["Application"] = relationship(  # noqa: F821
        "Application", back_populates="validation_runs", lazy="select"
    )
    findings: Mapped[list["ValidationFinding"]] = relationship(
        "ValidationFinding",
        back_populates="validation_run",
        lazy="select",
        cascade="all, delete-orphan",
    )


class ValidationFinding(Base):
    """A single rule evaluation result within a :class:`ValidationRun`."""

    __tablename__ = "validation_findings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    validation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(256), nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(FindingSeverity, name="findingseverity"), nullable=False
    )
    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus, name="findingstatus"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)

    # ── Relationships ────────────────────────────────────────────────────────
    validation_run: Mapped["ValidationRun"] = relationship(
        "ValidationRun", back_populates="findings", lazy="select"
    )
