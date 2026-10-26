"""
public_verify.py — Unauthenticated Public Verification Route with QR Code
AICTE AI-Powered Application Validation Platform

Anyone (students, parents, employers, regulators) can scan the QR code on the
approval letter to verify authenticity against the immutable hash-chained audit trail.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.application import Application, ApplicationStatus
from app.models.audit import AuditLog
from app.services.audit_chain import generate_qr_code_data_uri, verify_audit_chain

router = APIRouter(prefix="/public", tags=["public-verification"])


@router.get("/verify/{app_id}")
async def public_verify_application(
    app_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Publicly verify the authenticity of an AICTE Approval / EoA application.

    Zero-authentication required: Anyone holding the letter or scanning the QR code
    can inspect the cryptographically chained audit record.
    """
    app_result = await db.execute(select(Application).where(Application.id == app_id))
    app = app_result.scalar_one_or_none()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application record not found. The certificate or QR code is invalid.",
        )

    # Cryptographically verify the hash chain
    chain_report = await verify_audit_chain(db, app.id)

    # Find the official approval audit entry if approved
    audit_res = await db.execute(
        select(AuditLog)
        .where(AuditLog.application_id == app.id)
        .order_by(AuditLog.timestamp.desc())
    )
    audit_logs = list(audit_res.scalars().all())

    approval_entry = next(
        (
            log
            for log in audit_logs
            if "APPROV" in log.action or (log.result and "APPROV" in log.result)
        ),
        None,
    )

    is_approved = app.status in (
        ApplicationStatus.APPROVED_FOR_PROCESSING,
        ApplicationStatus.VALIDATION_COMPLETE,
    )

    # Determine base URL for public verification link
    # Typically frontend at http://localhost:3000/verify/{app_id}
    public_url = f"http://localhost:3000/verify/{app_id}"
    qr_data_uri = generate_qr_code_data_uri(public_url)

    decision_timeline = [
        {
            "id": str(log.id),
            "timestamp": log.timestamp.isoformat(),
            "actor": log.actor,
            "action": log.action.replace("OFFICER_ACTION_", ""),
            "result": log.result,
            "notes": log.notes,
            "entry_hash_short": (log.entry_hash or "N/A")[:16] + "...",
        }
        for log in audit_logs
    ]

    app_type_str = app.application_type.value if hasattr(app.application_type, "value") else str(app.application_type)

    return {
        "verification_status": "AUTHENTIC_RECORD_VERIFIED" if chain_report.get("is_valid") else "TAMPER_DETECTED",
        "application_id": str(app.id),
        "institution_name": app.institution_name,
        "academic_year": app.academic_year,
        "application_type": app_type_str.replace("_", " "),
        "current_status": app.status.value if hasattr(app.status, "value") else str(app.status),
        "is_approved": is_approved,
        "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
        "approval_date": approval_entry.timestamp.isoformat() if approval_entry else None,
        "approving_officer": approval_entry.actor if approval_entry else None,
        "chain_integrity": {
            "is_valid": chain_report.get("is_valid", False),
            "total_audit_events": chain_report.get("total_records", len(decision_timeline)),
            "chain_head_hash": chain_report.get("head_hash") or chain_report.get("recorded_hash") or "0" * 64,
            "genesis_hash": chain_report.get("genesis_hash", "0" * 64),
            "verification_message": chain_report.get("message", "Hash chain verified."),
        },
        "qr_code_data_uri": qr_data_uri,
        "public_verification_url": public_url,
        "decision_timeline": decision_timeline,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": (
            "This digital record is cryptographically verified via an append-only SHA-256 hash-chain. "
            "Any unauthorized alteration of the underlying decision logs breaks the cryptographic chain "
            "and immediately invalidates this certificate."
        ),
    }
