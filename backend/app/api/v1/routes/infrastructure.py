"""
infrastructure.py — Computer Vision & Physical Infrastructure Scrutiny Routes
AICTE AI-Powered Application Validation Platform
"""

from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.anomaly import AnomalyFlag
from app.models.application import Application, ApplicationStatus
from app.models.audit import AuditLog
from app.models.institution import InstitutionRecord
from app.models.user import User
from app.services.audit_chain import append_chained_audit_log
from app.services.vision.forensics import ImageForensicsService
from app.services.vision.geo_validator import GeoValidatorService
from app.services.vision.object_detector import InfrastructureObjectDetector

router = APIRouter(prefix="/applications/{app_id}/infrastructure", tags=["infrastructure"])

# Default AICTE registered coordinates for demo institution (Pune campus)
DEFAULT_CAMPUS_LAT = 18.520430
DEFAULT_CAMPUS_LON = 73.856744


async def _get_app_and_campus(
    app_id: uuid.UUID,
    db: AsyncSession,
) -> tuple[Application, float, float]:
    """Fetch application and its registered institutional coordinates."""
    app_result = await db.execute(select(Application).where(Application.id == app_id))
    app = app_result.scalar_one_or_none()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found."
        )

    campus_lat = DEFAULT_CAMPUS_LAT
    campus_lon = DEFAULT_CAMPUS_LON

    if app.institution_id:
        inst_res = await db.execute(
            select(InstitutionRecord).where(InstitutionRecord.id == app.institution_id)
        )
        inst = inst_res.scalar_one_or_none()
        if inst and getattr(inst, "latitude", None) and getattr(inst, "longitude", None):
            campus_lat = float(inst.latitude)
            campus_lon = float(inst.longitude)

    return app, campus_lat, campus_lon


@router.get("/campus-coordinates")
async def get_campus_coordinates(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return the official registered campus coordinates for this institution."""
    app, lat, lon = await _get_app_and_campus(app_id, db)
    return {
        "application_id": str(app_id),
        "institution_name": app.institution_name,
        "registered_campus_coordinates": {
            "latitude": lat,
            "longitude": lon,
            "address": "AICTE Registered Educational Campus",
        },
    }


@router.post("/analyze")
async def analyze_infrastructure_photo(
    app_id: uuid.UUID,
    file: UploadFile = File(..., description="Photographic or video-frame evidence"),
    facility_type: str = Form("COMPUTER_LAB", description="COMPUTER_LAB | CLASSROOM | LIBRARY"),
    live_latitude: Optional[float] = Form(None, description="Live browser geolocation latitude"),
    live_longitude: Optional[float] = Form(None, description="Live browser geolocation longitude"),
    live_accuracy: Optional[float] = Form(None, description="Accuracy in meters"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Analyze uploaded infrastructure photo for:
    1. Geotag / EXIF metadata vs. campus boundary & live applicant position.
    2. Error Level Analysis (ELA) for Photoshop tampering, altered signs/dates.
    3. Copy-Move Forgery Detection (cloned workstations/monitors).
    4. Object detection & equipment counting against AICTE APH regulatory requirements.
    """
    app, campus_lat, campus_lon = await _get_app_and_campus(app_id, db)

    # Save uploaded file to temp file for OpenCV / Pillow / EXIF processing
    suffix = Path(file.filename or "photo.jpg").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        # ── 1. Geolocation & EXIF Analysis ────────────────────────────────────
        geo_svc = GeoValidatorService()
        geo_result = geo_svc.verify_location_consistency(
            image_path=tmp_path,
            campus_lat=campus_lat,
            campus_lon=campus_lon,
            live_lat=live_latitude,
            live_lon=live_longitude,
        )

        # ── 2. Error Level Analysis (ELA) & Tampering Forensics ───────────────
        forensics_svc = ImageForensicsService()
        tamper_score, is_tampered, ela_heatmap_b64, ela_stats = forensics_svc.compute_ela(
            tmp_path
        )
        is_cloned, cloned_matches, clone_preview_b64 = (
            forensics_svc.detect_copy_move_forgery(tmp_path)
        )

        # ── 3. Equipment Scrutiny & Regulatory APH Norms ──────────────────────
        detector = InfrastructureObjectDetector()
        detection_result = detector.detect_and_count(
            image_path=tmp_path, facility_type=facility_type
        )

        # ── 4. Synthesize Overall Verdict ─────────────────────────────────────
        has_anomalies = (
            geo_result.get("risk_level") == "HIGH"
            or is_tampered
            or is_cloned
            or detection_result.get("compliance_status") == "DEFICIENT"
        )

        verdict = "VERIFIED_COMPLIANT"
        if is_tampered or is_cloned:
            verdict = "TAMPERING_SUSPECTED"
        elif geo_result.get("risk_level") == "HIGH":
            verdict = "LOCATION_MISMATCH"
        elif detection_result.get("compliance_status") == "DEFICIENT":
            verdict = "EQUIPMENT_DEFICIENT"

        # ── 5. Record Anomaly Flags in Database if Issues Found ───────────────
        now = datetime.now(timezone.utc)
        if is_tampered:
            anom = AnomalyFlag(
                id=uuid.uuid4(),
                application_id=app.id,
                check_type="IMAGE_COMPRESSION_TAMPERING",
                severity="HIGH",
                confidence=round(tamper_score / 100.0, 2),
                evidence=f"Error Level Analysis score {tamper_score}/100. Discontinuous localized error levels detected.",
                advisory_note="Preliminary image manipulation indicator. Inspect physical signboards/certificates.",
                created_at=now,
                is_reviewed=False,
            )
            db.add(anom)

        if is_cloned:
            anom_clone = AnomalyFlag(
                id=uuid.uuid4(),
                application_id=app.id,
                check_type="COPY_MOVE_FORGERY_DETECTED",
                severity="HIGH",
                confidence=0.89,
                evidence=f"{cloned_matches} identical duplicate feature patches found within the same photograph.",
                advisory_note="Suspected cloning of physical workstations or monitors.",
                created_at=now,
                is_reviewed=False,
            )
            db.add(anom_clone)

        for geo_flag in geo_result.get("anomaly_flags", []):
            anom_geo = AnomalyFlag(
                id=uuid.uuid4(),
                application_id=app.id,
                check_type=geo_flag["code"],
                severity=geo_flag["severity"],
                confidence=0.92,
                evidence=geo_flag["message"],
                advisory_note="Verify geographic coordinates of photo during physical inspection.",
                created_at=now,
                is_reviewed=False,
            )
            db.add(anom_geo)

        # Record in immutable cryptographic hash chain
        await append_chained_audit_log(
            db=db,
            actor=current_user.email,
            action="INFRASTRUCTURE_AI_SCRUTINY",
            application_id=app.id,
            result=verdict,
            notes=(
                f"Facility: {facility_type} | Tamper Score: {tamper_score}% | "
                f"Photo Distance: {geo_result.get('photo_to_campus_distance_meters')}m | "
                f"Equipment Compliance: {detection_result.get('compliance_status')}"
            ),
        )
        await db.commit()

        return {
            "application_id": str(app_id),
            "facility_type": facility_type,
            "overall_verdict": verdict,
            "has_critical_anomalies": has_anomalies,
            "location_analysis": geo_result,
            "forensics_analysis": {
                "tamper_score": tamper_score,
                "is_tampered": is_tampered,
                "is_cloned": is_cloned,
                "cloned_feature_pairs": cloned_matches,
                "ela_heatmap_base64": ela_heatmap_b64,
                "clone_preview_base64": clone_preview_b64,
                "stats": ela_stats,
            },
            "equipment_scrutiny": detection_result,
            "analyzed_at": now.isoformat(),
        }

    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
