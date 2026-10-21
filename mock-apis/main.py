"""
mock-apis/main.py

AICTE Validation Platform — Mock External Issuer API Server
============================================================
Simulates external verification APIs (DigiLocker, NAAC, State NOC,
Fire Department) with deterministic logic based on reference ID prefixes.

Prefix → behaviour:
  VALID-  → VERIFIED
  EXP-    → EXPIRED
  MM-     → MISMATCH_DETECTED
  NA-     → SOURCE_UNAVAILABLE
  (other) → MANUAL_REVIEW_REQUIRED
"""

from fastapi import FastAPI, Query
from pydantic import BaseModel
from datetime import datetime, date, timedelta
from typing import Optional
import random

app = FastAPI(
    title="AICTE Mock Issuer APIs",
    description=(
        "Deterministic mock server that simulates external document verification APIs "
        "used by the AICTE AI-Powered Validation Platform. Response status is driven "
        "by the prefix of the supplied reference/certificate number."
    ),
    version="0.1.0",
)

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────────


class VerificationResponse(BaseModel):
    status: str
    source: str
    issued_to: Optional[str] = None
    valid_till: Optional[str] = None
    issuing_authority: Optional[str] = None
    timestamp: str
    reference: Optional[str] = None
    details: Optional[dict] = None


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_TODAY = date.today()
_NOW_ISO = datetime.utcnow().isoformat() + "Z"


def _future(days: int) -> str:
    return (_TODAY + timedelta(days=days)).isoformat()


def _past(days: int) -> str:
    return (_TODAY - timedelta(days=days)).isoformat()


def _resolve_status(ref_id: Optional[str]) -> str:
    """Determine mock status from reference ID prefix."""
    if not ref_id:
        return "MANUAL_REVIEW_REQUIRED"
    ref_upper = ref_id.upper()
    if ref_upper.startswith("VALID-"):
        return "VERIFIED"
    if ref_upper.startswith("EXP-"):
        return "EXPIRED"
    if ref_upper.startswith("MM-"):
        return "MISMATCH_DETECTED"
    if ref_upper.startswith("NA-"):
        return "SOURCE_UNAVAILABLE"
    return "MANUAL_REVIEW_REQUIRED"


def _build_response(
    status: str,
    source: str,
    ref: Optional[str],
    institution: Optional[str] = None,
    authority: str = "Unknown Authority",
) -> VerificationResponse:
    """Build a VerificationResponse based on computed status."""

    issued_to = institution or "ABC Institute of Technology"
    now = datetime.utcnow().isoformat() + "Z"

    if status == "VERIFIED":
        return VerificationResponse(
            status=status,
            source=source,
            issued_to=issued_to,
            valid_till=_future(365),
            issuing_authority=authority,
            timestamp=now,
            reference=ref,
            details={
                "verification_mode": "automated",
                "confidence": 0.98,
                "remarks": "Document verified successfully against issuer records.",
            },
        )

    if status == "EXPIRED":
        return VerificationResponse(
            status=status,
            source=source,
            issued_to=issued_to,
            valid_till=_past(30),
            issuing_authority=authority,
            timestamp=now,
            reference=ref,
            details={
                "verification_mode": "automated",
                "confidence": 0.97,
                "remarks": "Document found in issuer records but validity period has elapsed.",
                "expired_on": _past(30),
            },
        )

    if status == "MISMATCH_DETECTED":
        return VerificationResponse(
            status=status,
            source=source,
            issued_to=None,
            valid_till=None,
            issuing_authority=authority,
            timestamp=now,
            reference=ref,
            details={
                "verification_mode": "automated",
                "confidence": 0.85,
                "remarks": (
                    "Data on the submitted document does not match issuer records. "
                    "Institution name or certificate number mismatch detected."
                ),
                "mismatched_fields": ["institution_name"],
            },
        )

    if status == "SOURCE_UNAVAILABLE":
        return VerificationResponse(
            status=status,
            source=source,
            issued_to=None,
            valid_till=None,
            issuing_authority=None,
            timestamp=now,
            reference=ref,
            details={
                "verification_mode": "automated",
                "remarks": (
                    "External issuer system is temporarily unavailable. "
                    "Please retry after some time or proceed with manual verification."
                ),
                "retry_after_minutes": 30,
            },
        )

    # MANUAL_REVIEW_REQUIRED (default)
    return VerificationResponse(
        status=status,
        source=source,
        issued_to=None,
        valid_till=None,
        issuing_authority=authority,
        timestamp=now,
        reference=ref,
        details={
            "verification_mode": "manual",
            "remarks": (
                "Reference ID not found in issuer records or format unrecognised. "
                "Document has been flagged for manual review by a verification officer."
            ),
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@app.get(
    "/mock/digilocker/verify",
    response_model=VerificationResponse,
    summary="DigiLocker Document Verification",
    tags=["DigiLocker"],
)
def verify_digilocker(
    ref_id: Optional[str] = Query(default=None, description="DigiLocker reference ID"),
    doc_type: Optional[str] = Query(
        default=None,
        description="Document type (e.g., AFFIDAVIT, STATE_NOC, LAND_BUILDING_DOC)",
    ),
):
    """
    Simulate verification of a document against the DigiLocker repository.

    - **VALID-\\*** → `VERIFIED`
    - **EXP-\\*** → `EXPIRED`
    - **MM-\\*** → `MISMATCH_DETECTED`
    - **NA-\\*** → `SOURCE_UNAVAILABLE`
    - anything else → `MANUAL_REVIEW_REQUIRED`
    """
    status = _resolve_status(ref_id)
    return _build_response(
        status=status,
        source="DigiLocker",
        ref=ref_id,
        authority="Ministry of Electronics and Information Technology (MeitY)",
    )


@app.get(
    "/mock/naac/verify",
    response_model=VerificationResponse,
    summary="NAAC Accreditation Certificate Verification",
    tags=["NAAC"],
)
def verify_naac(
    cert_no: Optional[str] = Query(default=None, description="NAAC certificate number"),
    institution: Optional[str] = Query(
        default=None, description="Institution name as on certificate"
    ),
):
    """
    Simulate verification of a NAAC Accreditation Certificate.

    Uses **cert_no** prefix to determine the response status.
    """
    status = _resolve_status(cert_no)
    response = _build_response(
        status=status,
        source="NAAC Portal",
        ref=cert_no,
        institution=institution,
        authority="National Assessment and Accreditation Council (NAAC)",
    )

    # Augment with NAAC-specific grade data when verified
    if status == "VERIFIED":
        grade_info = {"grade": "A+", "cgpa": 3.42, "cycle": "3rd", "valid_till": _future(365 * 5)}
        if response.details:
            response.details.update(grade_info)
        else:
            response.details = grade_info

    return response


@app.get(
    "/mock/state-noc/verify",
    response_model=VerificationResponse,
    summary="State Government NOC Verification",
    tags=["State NOC"],
)
def verify_state_noc(
    ref_id: Optional[str] = Query(default=None, description="State NOC reference ID"),
    state: Optional[str] = Query(
        default=None, description="State name (e.g., Maharashtra, Karnataka)"
    ),
):
    """
    Simulate verification of a State No-Objection Certificate (NOC) with the
    respective State Government portal.
    """
    state_label = state or "Maharashtra"
    authority = f"{state_label} State Government — Technical Education Department"
    status = _resolve_status(ref_id)
    response = _build_response(
        status=status,
        source=f"{state_label} State NOC Portal",
        ref=ref_id,
        authority=authority,
    )

    if status == "VERIFIED" and response.details:
        response.details["state"] = state_label
        response.details["noc_type"] = "Technical Institution"

    return response


@app.get(
    "/mock/fire-dept/verify",
    response_model=VerificationResponse,
    summary="Fire Department NOC / Safety Certificate Verification",
    tags=["Fire Department"],
)
def verify_fire_dept(
    cert_no: Optional[str] = Query(
        default=None, description="Fire Safety Certificate number"
    ),
    district: Optional[str] = Query(
        default=None, description="District where institution is located"
    ),
):
    """
    Simulate verification of a Fire Safety / NOC Certificate with the local
    Fire Department records.
    """
    district_label = district or "Pune"
    authority = f"{district_label} District Fire Department"
    status = _resolve_status(cert_no)
    response = _build_response(
        status=status,
        source=f"{district_label} Fire Department Portal",
        ref=cert_no,
        authority=authority,
    )

    if status == "VERIFIED" and response.details:
        response.details["district"] = district_label
        response.details["certificate_type"] = "Fire Safety NOC"
        response.details["building_category"] = "Educational Institution"

    return response


# ─────────────────────────────────────────────────────────────────────────────
# POST endpoints compatible with validation_tasks
# ─────────────────────────────────────────────────────────────────────────────


class GenericVerifyPayload(BaseModel):
    reference: Optional[str] = None
    institution_name: Optional[str] = None
    grade: Optional[str] = None
    ref_id: Optional[str] = None


@app.post("/verify/naac", response_model=VerificationResponse, tags=["NAAC"])
def verify_naac_post(payload: GenericVerifyPayload):
    cert_no = payload.reference or payload.ref_id
    status = _resolve_status(cert_no)
    response = _build_response(
        status=status,
        source="NAAC Portal",
        ref=cert_no,
        institution=payload.institution_name,
        authority="National Assessment and Accreditation Council (NAAC)",
    )
    if status == "VERIFIED":
        grade_info = {"grade": payload.grade or "A+", "cgpa": 3.42, "cycle": "3rd", "valid_till": _future(365 * 5)}
        if response.details:
            response.details.update(grade_info)
        else:
            response.details = grade_info
    return response


@app.post("/verify/ter", response_model=VerificationResponse, tags=["TER"])
def verify_ter_post(payload: GenericVerifyPayload):
    ref_id = payload.reference or payload.ref_id
    status = _resolve_status(ref_id)
    return _build_response(
        status=status,
        source="Fee Regulatory Authority (TER)",
        ref=ref_id,
        institution=payload.institution_name,
        authority="State Fee Regulatory Authority",
    )


@app.post("/verify/affidavit", response_model=VerificationResponse, tags=["Affidavit"])
def verify_affidavit_post(payload: GenericVerifyPayload):
    ref_id = payload.reference or payload.ref_id
    status = _resolve_status(ref_id)
    return _build_response(
        status=status,
        source="Notary & Judicial Registry",
        ref=ref_id,
        authority="State Notary Services Portal",
    )


@app.post("/verify/noc", response_model=VerificationResponse, tags=["State NOC"])
def verify_noc_post(payload: GenericVerifyPayload):
    ref_id = payload.reference or payload.ref_id
    status = _resolve_status(ref_id)
    return _build_response(
        status=status,
        source="State NOC Portal",
        ref=ref_id,
        institution=payload.institution_name,
        authority="Directorate of Technical Education",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────


@app.get("/health", tags=["Health"])
def health():
    """Returns 200 OK when the mock API server is running."""
    return {"status": "ok", "service": "AICTE Mock Issuer APIs", "version": "0.1.0"}
