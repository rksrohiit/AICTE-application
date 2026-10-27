"""Checklist and live workflow status APIs."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.application import Application
from app.models.document import Document
from app.models.user import User, UserRole
from app.services.checklist import evaluate_checklist

router = APIRouter(prefix="/applications", tags=["checklist"])


async def _application(app_id: uuid.UUID, db: AsyncSession, user: User) -> Application:
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if app is None or (user.role == UserRole.INSTITUTION and app.institution_id != user.institution_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    return app


@router.get("/{app_id}/checklist", summary="Evaluate the configured application checklist")
async def get_checklist(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    app = await _application(app_id, db, current_user)
    result = await db.execute(select(Document).where(Document.application_id == app_id))
    items = evaluate_checklist(app, list(result.scalars().all()))
    counts = {key: sum(1 for item in items if item["status"].value == key) for key in ("PASS", "FAIL", "WARN", "SKIPPED")}
    return {
        "application_id": str(app_id),
        "application_type": app.application_type.value,
        "rules_version": "1.0.0",
        "items": [{**item, "status": item["status"].value} for item in items],
        "counts": counts,
        "completion_percent": round(((counts["PASS"] + counts["FAIL"] + counts["WARN"]) / len(items) * 100) if items else 0, 2),
    }


@router.get("/{app_id}/workflow-status", summary="Get live OCR, validation, anomaly and verification status")
async def get_workflow_status(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    app = await _application(app_id, db, current_user)
    result = await db.execute(select(Document).where(Document.application_id == app_id))
    documents = list(result.scalars().all())
    ocr = {key: sum(1 for doc in documents if getattr(doc.ocr_status, "value", doc.ocr_status) == key) for key in ("PENDING", "PROCESSING", "COMPLETE", "FAILED")}
    return {
        "application_id": str(app_id),
        "application_status": app.status.value,
        "documents": {"total": len(documents), "ocr": ocr},
        "is_processing": app.status.value == "UNDER_VALIDATION" or ocr["PENDING"] > 0 or ocr["PROCESSING"] > 0,
        "last_updated": app.updated_at,
    }
