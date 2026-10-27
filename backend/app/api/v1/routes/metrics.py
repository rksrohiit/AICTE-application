"""
Metrics summary route.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_officer
from app.models.application import Application, ApplicationStatus
from app.models.document import Document
from app.models.validation import ValidationRun
from app.models.anomaly import AnomalyFlag
from app.models.user import User

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get(
    "/summary",
    summary="Aggregate platform metrics (officer access)",
)
async def get_metrics_summary(
    db: AsyncSession = Depends(get_db),
    _officer: User = Depends(require_officer),
) -> Dict[str, Any]:
    """Return aggregate statistics across all applications.

    Args:
        db:       Async database session.
        _officer: Authenticated officer (access guard only).

    Returns:
        A dict containing counts by status, document counts, anomaly counts,
        and validation score distribution.
    """
    # ── Application counts by status ────────────────────────────────────────
    status_rows = await db.execute(
        select(Application.status, func.count(Application.id).label("cnt"))
        .group_by(Application.status)
    )
    status_counts: Dict[str, int] = {row.status.value: row.cnt for row in status_rows}

    # ── Total applications ──────────────────────────────────────────────────
    total_apps_row = await db.execute(select(func.count(Application.id)))
    total_applications: int = total_apps_row.scalar_one() or 0

    # ── Total documents ─────────────────────────────────────────────────────
    total_docs_row = await db.execute(select(func.count(Document.id)))
    total_documents: int = total_docs_row.scalar_one() or 0

    # ── Anomaly counts by severity ──────────────────────────────────────────
    anomaly_rows = await db.execute(
        select(AnomalyFlag.severity, func.count(AnomalyFlag.id).label("cnt"))
        .group_by(AnomalyFlag.severity)
    )
    anomaly_counts: Dict[str, int] = {row.severity: row.cnt for row in anomaly_rows}
    unresolved_anomalies = await db.scalar(
        select(func.count(AnomalyFlag.id)).where(AnomalyFlag.is_reviewed.is_(False))
    ) or 0
    pending_review = await db.scalar(
        select(func.count(Application.id)).where(
            Application.status.in_(
                [
                    ApplicationStatus.SUBMITTED,
                    ApplicationStatus.VALIDATION_COMPLETE,
                    ApplicationStatus.UNDER_REVIEW,
                    ApplicationStatus.ESCALATED,
                    ApplicationStatus.SENT_FOR_RECTIFICATION,
                ]
            )
        )
    ) or 0

    # ── Validation score stats ──────────────────────────────────────────────
    score_row = await db.execute(
        select(
            func.avg(ValidationRun.overall_score).label("avg_score"),
            func.min(ValidationRun.overall_score).label("min_score"),
            func.max(ValidationRun.overall_score).label("max_score"),
        )
    )
    score_stats = score_row.one()

    return {
        "total_applications": total_applications,
        "applications_by_status": status_counts,
        "total_documents_uploaded": total_documents,
        "anomalies_by_severity": anomaly_counts,
        "validation_scores": {
            "average": round(float(score_stats.avg_score or 0), 2),
            "minimum": score_stats.min_score or 0,
            "maximum": score_stats.max_score or 0,
        },
        "pending_review": pending_review,
        "anomalies_flagged": unresolved_anomalies,
        "verified_today": 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
