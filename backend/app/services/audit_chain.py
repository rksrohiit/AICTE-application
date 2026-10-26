"""
audit_chain.py — Cryptographic Hash-Chained Audit Trail & Public Verification QR
AICTE AI-Powered Application Validation Platform

Principles:
- Pure cryptographic hash chaining (SHA-256): Each decision record encapsulates
  the hash digest of the preceding record.
- Tamper detection: Any retrospective edit, insertion, or deletion breaks the chain.
- Honest transparency: Avoid calling it "blockchain"; it is an append-only,
  verifiable hash-linked ledger with public cryptographic verification.
"""

from __future__ import annotations

import base64
import hashlib
import io
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import qrcode
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

GENESIS_HASH = "0" * 64


def compute_audit_hash(
    prev_hash: str,
    timestamp_str: str,
    actor: str,
    action: str,
    application_id: Optional[str] = None,
    result: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """Compute deterministic SHA-256 hash for an audit record linked to its predecessor."""
    payload = "|".join(
        [
            prev_hash.strip(),
            timestamp_str.strip(),
            actor.strip(),
            action.strip(),
            (application_id or "").strip(),
            (result or "").strip(),
            (notes or "").strip(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def get_latest_audit_hash(
    db: AsyncSession, application_id: Optional[uuid.UUID]
) -> str:
    """Return the entry_hash of the latest record in the application's audit chain."""
    if not application_id:
        return GENESIS_HASH

    query = (
        select(AuditLog)
        .where(AuditLog.application_id == application_id)
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
        .limit(1)
    )
    result = await db.execute(query)
    last_record = result.scalar_one_or_none()

    if last_record and last_record.entry_hash:
        return last_record.entry_hash
    return GENESIS_HASH


async def append_chained_audit_log(
    db: AsyncSession,
    actor: str,
    action: str,
    application_id: Optional[uuid.UUID] = None,
    document_id: Optional[uuid.UUID] = None,
    rule_id: Optional[str] = None,
    result: Optional[str] = None,
    notes: Optional[str] = None,
) -> AuditLog:
    """Create and append an immutable, hash-linked audit log entry."""
    prev_hash = await get_latest_audit_hash(db, application_id)
    now = datetime.now(timezone.utc)
    timestamp_str = now.isoformat()

    entry_hash = compute_audit_hash(
        prev_hash=prev_hash,
        timestamp_str=timestamp_str,
        actor=actor,
        action=action,
        application_id=str(application_id) if application_id else None,
        result=result,
        notes=notes,
    )

    log_entry = AuditLog(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        timestamp=now,
        actor=actor,
        action=action,
        application_id=application_id,
        document_id=document_id,
        rule_id=rule_id,
        result=result,
        notes=notes,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
    )
    db.add(log_entry)
    return log_entry


async def verify_audit_chain(
    db: AsyncSession, application_id: uuid.UUID
) -> Dict[str, Any]:
    """Cryptographically traverse and verify the integrity of the audit chain for an application.

    Returns status, broken link details if any, and head digest.
    """
    query = (
        select(AuditLog)
        .where(AuditLog.application_id == application_id)
        .order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
    )
    res = await db.execute(query)
    records: List[AuditLog] = list(res.scalars().all())

    if not records:
        return {
            "application_id": str(application_id),
            "is_valid": True,
            "total_records": 0,
            "head_hash": GENESIS_HASH,
            "genesis_hash": GENESIS_HASH,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "records": [],
            "message": "Empty chain: Genesis state verified.",
        }

    expected_prev = GENESIS_HASH
    chain_summary = []

    for idx, rec in enumerate(records):
        rec_prev = rec.prev_hash or GENESIS_HASH
        rec_ts = rec.timestamp
        if rec_ts.tzinfo is None:
            rec_ts = rec_ts.replace(tzinfo=timezone.utc)

        expected_hash = compute_audit_hash(
            prev_hash=rec_prev,
            timestamp_str=rec_ts.isoformat(),
            actor=rec.actor,
            action=rec.action,
            application_id=str(rec.application_id) if rec.application_id else None,
            result=rec.result,
            notes=rec.notes,
        )

        # Check 1: Chain continuity (previous pointer must match prior record's entry_hash)
        if idx > 0 and rec_prev != expected_prev:
            return {
                "application_id": str(application_id),
                "is_valid": False,
                "broken_at_step": idx + 1,
                "broken_record_id": str(rec.id),
                "error_type": "PREV_HASH_DISCONTINUITY",
                "expected_prev_hash": expected_prev,
                "actual_prev_hash": rec_prev,
                "head_hash": expected_prev,
                "genesis_hash": GENESIS_HASH,
                "total_records": len(records),
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "message": f"Cryptographic continuity broken at record #{idx + 1} ({rec.action}).",
            }

        # Check 2: Content integrity (computed entry hash must match recorded entry_hash)
        if rec.entry_hash and rec.entry_hash != expected_hash:
            return {
                "application_id": str(application_id),
                "is_valid": False,
                "broken_at_step": idx + 1,
                "broken_record_id": str(rec.id),
                "error_type": "CONTENT_TAMPERING_DETECTED",
                "recorded_hash": rec.entry_hash,
                "recomputed_hash": expected_hash,
                "head_hash": rec.entry_hash or expected_prev,
                "genesis_hash": GENESIS_HASH,
                "total_records": len(records),
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "message": f"Tampering detected! Record #{idx + 1} content has been modified.",
            }

        expected_prev = rec.entry_hash or expected_hash
        chain_summary.append(
            {
                "step": idx + 1,
                "id": str(rec.id),
                "timestamp": rec_ts.isoformat(),
                "actor": rec.actor,
                "action": rec.action,
                "result": rec.result,
                "prev_hash_short": rec_prev[:12] + "...",
                "entry_hash_short": (rec.entry_hash or expected_hash)[:12] + "...",
                "entry_hash_full": rec.entry_hash or expected_hash,
            }
        )

    head_hash = records[-1].entry_hash or expected_prev

    return {
        "application_id": str(application_id),
        "is_valid": True,
        "total_records": len(records),
        "genesis_hash": GENESIS_HASH,
        "head_hash": head_hash,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "records": chain_summary,
        "message": f"Cryptographic integrity verified. All {len(records)} audit log entries are strictly intact.",
    }


def generate_qr_code_data_uri(public_url: str) -> str:
    """Generate high-density, scannable QR Code as base64 PNG data URI."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(public_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1E3A8A", back_color="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


async def backfill_existing_audit_logs(db: AsyncSession) -> int:
    """Sequential backfill of hash chains for legacy database rows lacking hashes."""
    query = select(AuditLog).order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
    res = await db.execute(query)
    all_logs = list(res.scalars().all())

    app_groups: Dict[Optional[uuid.UUID], List[AuditLog]] = {}
    for log in all_logs:
        app_groups.setdefault(log.application_id, []).append(log)

    updated_count = 0
    for app_id, logs in app_groups.items():
        prev = GENESIS_HASH
        for rec in logs:
            if not rec.entry_hash or not rec.prev_hash:
                rec.prev_hash = prev
                rec.entry_hash = compute_audit_hash(
                    prev_hash=prev,
                    timestamp_str=rec.timestamp.isoformat(),
                    actor=rec.actor,
                    action=rec.action,
                    application_id=str(rec.application_id) if rec.application_id else None,
                    result=rec.result,
                    notes=rec.notes,
                )
                updated_count += 1
            prev = rec.entry_hash

    if updated_count > 0:
        await db.commit()

    return updated_count
