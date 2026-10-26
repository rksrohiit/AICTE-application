"""
Document ORM model — uploaded files attached to an application.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DocumentType(str, enum.Enum):
    """Enumeration of all mandatory document types accepted by the platform."""

    AFFIDAVIT = "AFFIDAVIT"
    STATE_NOC = "STATE_NOC"
    NAAC_CERT = "NAAC_CERT"
    FIRE_SAFETY_CERT = "FIRE_SAFETY_CERT"
    TER_RECEIPT = "TER_RECEIPT"
    LAND_BUILDING_DOC = "LAND_BUILDING_DOC"
    FACULTY_DATA = "FACULTY_DATA"
    EOA_FORM = "EOA_FORM"


class OCRStatus(str, enum.Enum):
    """Processing status for the OCR pipeline."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class Document(Base):
    """A document file uploaded as part of an application."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doc_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="documenttype"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/pdf")
    ocr_status: Mapped[OCRStatus] = mapped_column(
        Enum(OCRStatus, name="ocrstatus"),
        nullable=False,
        default=OCRStatus.PENDING,
    )
    processing_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="UPLOADED"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extracted_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    extracted_claims: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=None)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
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
    application: Mapped["Application"] = relationship(  # noqa: F821
        "Application", back_populates="documents", lazy="select"
    )
    verification_results: Mapped[list["VerificationResult"]] = relationship(  # noqa: F821
        "VerificationResult", back_populates="document", lazy="select", cascade="all, delete-orphan"
    )
    anomaly_flags: Mapped[list["AnomalyFlag"]] = relationship(  # noqa: F821
        "AnomalyFlag", back_populates="document", lazy="select", cascade="all, delete-orphan"
    )
