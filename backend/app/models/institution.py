"""
InstitutionRecord ORM model — mirrors AICTE's internal institutional data.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InstitutionRecord(Base):
    """Snapshot of AICTE-held data for a registered institution."""

    __tablename__ = "institution_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    aicte_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    state: Mapped[str] = mapped_column(String(128), nullable=False)
    district: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_intake: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approved_programmes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    previous_eoa_status: Mapped[str] = mapped_column(String(64), nullable=False, default="UNKNOWN")
    deficiency_history: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    ter_payment_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    naac_grade: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────────────────────────
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        "User", back_populates="institution", lazy="select"
    )
    applications: Mapped[list["Application"]] = relationship(  # noqa: F821
        "Application", back_populates="institution", lazy="select"
    )
