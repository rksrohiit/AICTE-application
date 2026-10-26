"""
Validation Celery task: run all rules against an application and persist findings.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.tasks.celery_app import celery_app

# ── Sync engine (Celery workers are synchronous) ──────────────────────────────
sync_db_url = settings.DATABASE_URL
if "sqlite+aiosqlite://" in sync_db_url:
    sync_db_url = sync_db_url.replace("sqlite+aiosqlite://", "sqlite://")
elif "postgresql+asyncpg://" in sync_db_url:
    sync_db_url = sync_db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
elif "postgresql://" in sync_db_url and "psycopg2" not in sync_db_url:
    sync_db_url = sync_db_url.replace("postgresql://", "postgresql+psycopg2://")

_sync_kwargs: Dict[str, Any] = {}
if "sqlite" in sync_db_url:
    _sync_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _sync_kwargs["pool_pre_ping"] = True
    _sync_kwargs["pool_size"] = 5
    _sync_kwargs["max_overflow"] = 10

_sync_engine = create_engine(sync_db_url, **_sync_kwargs)
SyncSession = sessionmaker(bind=_sync_engine, autoflush=False, autocommit=False)

# ── Rules YAML path ────────────────────────────────────────────────────────────
_RULES_DIR = Path(__file__).resolve().parents[3] / "rules"


def _load_rules() -> List[Dict[str, Any]]:
    """Load validation rules from YAML files in the rules directory.

    Returns:
        Flat list of rule dicts, each containing at minimum:
        ``id``, ``name``, ``category``, ``severity``, ``description``.
    """
    rules: List[Dict[str, Any]] = []
    if not _RULES_DIR.exists():
        return rules
    for yaml_file in sorted(_RULES_DIR.glob("*.yaml")):
        try:
            with yaml_file.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if isinstance(data, dict) and "rules" in data:
                rules.extend(data["rules"])
            elif isinstance(data, list):
                rules.extend(data)
        except Exception:
            continue
    return rules


def _evaluate_rule(
    rule: Dict[str, Any],
    app: Any,
    documents: List[Any],
    db: Session,
) -> Dict[str, Any]:
    """Evaluate a single validation rule against the application state.

    Args:
        rule:      Rule definition dict.
        app:       The :class:`~app.models.application.Application` ORM object.
        documents: List of :class:`~app.models.document.Document` ORM objects.
        db:        Active synchronous DB session.

    Returns:
        A dict with keys ``status``, ``message``, ``evidence``, and ``document_id``.
    """
    from app.models.document import DocumentType, OCRStatus
    from app.models.validation import FindingStatus

    rule_id: str = rule.get("id", "UNKNOWN")
    rule_category: str = rule.get("category", "GENERAL")

    # ── DOCUMENT_PRESENCE rules ───────────────────────────────────────────────
    if rule_category == "DOCUMENT_PRESENCE":
        required_type: str = rule.get("required_doc_type", "")
        matching = [d for d in documents if d.doc_type.value == required_type]
        if matching:
            return {
                "status": FindingStatus.PASS,
                "message": f"Required document '{required_type}' is present.",
                "evidence": f"Document ID: {matching[0].id}",
                "document_id": str(matching[0].id),
            }
        return {
            "status": FindingStatus.FAIL,
            "message": f"Required document '{required_type}' is missing.",
            "evidence": "No document of this type was uploaded.",
            "document_id": None,
        }

    # ── OCR_COMPLETE rules ────────────────────────────────────────────────────
    if rule_category == "OCR_COMPLETE":
        required_type = rule.get("required_doc_type", "")
        matching = [d for d in documents if d.doc_type.value == required_type]
        if not matching:
            return {
                "status": FindingStatus.SKIPPED,
                "message": f"Document '{required_type}' not uploaded; skipping OCR check.",
                "evidence": None,
                "document_id": None,
            }
        doc = matching[0]
        if doc.ocr_status == OCRStatus.COMPLETE:
            return {
                "status": FindingStatus.PASS,
                "message": f"OCR completed successfully for '{required_type}'.",
                "evidence": f"Document ID: {doc.id}",
                "document_id": str(doc.id),
            }
        return {
            "status": FindingStatus.FAIL,
            "message": f"OCR failed or pending for '{required_type}'.",
            "evidence": f"OCR status: {doc.ocr_status.value}",
            "document_id": str(doc.id),
        }

    # ── FIELD_PRESENT rules ───────────────────────────────────────────────────
    if rule_category == "FIELD_PRESENT":
        required_type = rule.get("required_doc_type", "")
        field_name: str = rule.get("field", "")
        matching = [d for d in documents if d.doc_type.value == required_type]
        if not matching:
            return {
                "status": FindingStatus.SKIPPED,
                "message": f"Document '{required_type}' not found; cannot check field '{field_name}'.",
                "evidence": None,
                "document_id": None,
            }
        doc = matching[0]
        extracted = doc.extracted_data or {}
        fields = extracted.get("fields", {})
        field_val = fields.get(field_name, {}).get("value")
        if field_val:
            return {
                "status": FindingStatus.PASS,
                "message": f"Field '{field_name}' present in '{required_type}'.",
                "evidence": f"Value: {field_val}",
                "document_id": str(doc.id),
            }
        return {
            "status": FindingStatus.WARN,
            "message": f"Field '{field_name}' not extracted from '{required_type}'.",
            "evidence": "Value was empty or not detected by OCR.",
            "document_id": str(doc.id),
        }

    # ── APPLICATION_STATUS rules ──────────────────────────────────────────────
    if rule_category == "APPLICATION_STATUS":
        from app.models.application import ApplicationStatus

        expected_status: str = rule.get("expected_status", "SUBMITTED")
        if app.status.value == expected_status or app.status != "DRAFT":
            return {
                "status": FindingStatus.PASS,
                "message": f"Application status '{app.status.value}' is acceptable.",
                "evidence": None,
                "document_id": None,
            }
        return {
            "status": FindingStatus.FAIL,
            "message": f"Application is still in DRAFT status.",
            "evidence": f"Current status: {app.status.value}",
            "document_id": None,
        }

    # ── CONSISTENCY / CROSS_DOCUMENT rules ────────────────────────────────────
    if rule_category == "CONSISTENCY" or rule.get("check_type") == "cross_doc_field_match":
        from app.services.cross_document import CrossDocumentConsistencyEngine

        consistency_rep = CrossDocumentConsistencyEngine.analyze_documents(app.id, documents)
        target_field = rule.get("field", "institution_name")
        match_finding = next((f for f in consistency_rep.findings if f.field == target_field), None)

        if match_finding:
            if match_finding.status == "CONSISTENT":
                return {
                    "status": FindingStatus.PASS,
                    "message": match_finding.explanation,
                    "evidence": f"Similarity score: {int(match_finding.similarity_score * 100)}% across {len(match_finding.evidence)} source documents.",
                    "document_id": match_finding.evidence[0].document_id if match_finding.evidence else None,
                }
            elif match_finding.status == "NEEDS_REVIEW":
                return {
                    "status": FindingStatus.WARN,
                    "message": match_finding.explanation,
                    "evidence": f"Advisory: {match_finding.resolution_guidance}",
                    "document_id": match_finding.evidence[0].document_id if match_finding.evidence else None,
                }
            else:
                return {
                    "status": FindingStatus.FAIL,
                    "message": match_finding.explanation,
                    "evidence": f"Discrepancy: {match_finding.resolution_guidance}",
                    "document_id": match_finding.evidence[0].document_id if match_finding.evidence else None,
                }

        return {
            "status": FindingStatus.SKIPPED,
            "message": f"Insufficient document claims uploaded to evaluate cross-document consistency for '{target_field}'.",
            "evidence": None,
            "document_id": None,
        }

    # ── Default: skip unknown rule categories ─────────────────────────────────
    return {
        "status": FindingStatus.SKIPPED,
        "message": f"Rule category '{rule_category}' is not implemented.",
        "evidence": None,
        "document_id": None,
    }


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    name="app.tasks.validation_tasks.run_validation",
)
def run_validation(self, application_id: str) -> Dict[str, Any]:
    """Run the full validation pipeline for a submitted application.

    Steps:
    1. Create a :class:`~app.models.validation.ValidationRun` record (status=RUNNING).
    2. Load rules from the ``rules/`` YAML files.
    3. For each rule, evaluate and persist a :class:`~app.models.validation.ValidationFinding`.
    4. Compute the overall score (percentage of PASS findings).
    5. Update the :class:`~app.models.validation.ValidationRun` record (status=COMPLETE).
    6. Trigger anomaly detection and verification subtasks.
    7. Transition the application to VALIDATION_COMPLETE.
    8. Write :class:`~app.models.audit.AuditLog` entries.

    Args:
        application_id: UUID string of the :class:`~app.models.application.Application`.

    Returns:
        Dict summarising the run outcome.
    """
    from app.models.application import Application, ApplicationStatus
    from app.models.audit import AuditLog
    from app.models.document import Document
    from app.models.validation import FindingSeverity, FindingStatus, RunStatus, ValidationFinding, ValidationRun

    db: Session = SyncSession()

    try:
        app_uuid = uuid.UUID(application_id)
        app: Application | None = db.get(Application, app_uuid)

        if app is None:
            return {"error": f"Application {application_id} not found."}

        # ── Create ValidationRun ───────────────────────────────────────────────
        rules = _load_rules()
        run = ValidationRun(
            application_id=app_uuid,
            status=RunStatus.RUNNING,
            rules_version="1.0.0",
        )
        db.add(run)
        db.flush()

        audit_start = AuditLog(
            actor="SYSTEM",
            action="VALIDATION_STARTED",
            application_id=app_uuid,
            result="RUNNING",
            notes=f"Rules count: {len(rules)}",
        )
        db.add(audit_start)
        db.commit()

        # ── Load documents ────────────────────────────────────────────────────
        documents: List[Document] = (
            db.query(Document).filter(Document.application_id == app_uuid).all()
        )

        # ── Evaluate each rule ────────────────────────────────────────────────
        findings: List[ValidationFinding] = []
        count_high = count_medium = count_low = 0
        pass_count = 0
        total_evaluatable = 0

        for rule in rules:
            result = _evaluate_rule(rule, app, documents, db)

            severity_str: str = rule.get("severity", "MEDIUM").upper()
            try:
                severity = FindingSeverity(severity_str)
            except ValueError:
                severity = FindingSeverity.MEDIUM

            finding = ValidationFinding(
                validation_run_id=run.id,
                rule_id=rule.get("id", "UNKNOWN"),
                rule_name=rule.get("name", rule.get("id", "Unknown Rule")),
                severity=severity,
                status=result["status"],
                document_id=uuid.UUID(result["document_id"]) if result.get("document_id") else None,
                evidence=result.get("evidence"),
                message=result["message"],
                category=rule.get("category", "GENERAL"),
            )
            findings.append(finding)
            db.add(finding)

            if result["status"] != FindingStatus.SKIPPED:
                total_evaluatable += 1
                if result["status"] == FindingStatus.PASS:
                    pass_count += 1

            if severity == FindingSeverity.HIGH:
                count_high += 1
            elif severity == FindingSeverity.MEDIUM:
                count_medium += 1
            else:
                count_low += 1

        # ── Compute overall score ─────────────────────────────────────────────
        overall_score = int((pass_count / total_evaluatable * 100) if total_evaluatable > 0 else 0)

        # ── Update ValidationRun ──────────────────────────────────────────────
        run.status = RunStatus.COMPLETE
        run.completed_at = datetime.now(timezone.utc)
        run.overall_score = overall_score
        run.findings_count_high = count_high
        run.findings_count_medium = count_medium
        run.findings_count_low = count_low

        # ── Transition application status ─────────────────────────────────────
        app.status = ApplicationStatus.VALIDATION_COMPLETE
        app.updated_at = datetime.now(timezone.utc)

        audit_done = AuditLog(
            actor="SYSTEM",
            action="VALIDATION_COMPLETE",
            application_id=app_uuid,
            result=f"SCORE:{overall_score}",
            notes=(
                f"Findings — HIGH:{count_high} MEDIUM:{count_medium} LOW:{count_low}. "
                f"Total rules evaluated: {total_evaluatable}, passed: {pass_count}."
            ),
        )
        db.add(audit_done)
        db.commit()

        # ── Trigger downstream subtasks ───────────────────────────────────────
        try:
            from app.tasks.validation_tasks import run_anomaly_detection, run_verification

            run_anomaly_detection.delay(application_id)
            run_verification.delay(application_id)
        except Exception:
            pass  # subtask failures should not block the main validation result

        return {
            "application_id": application_id,
            "validation_run_id": str(run.id),
            "overall_score": overall_score,
            "status": "COMPLETE",
            "findings_high": count_high,
            "findings_medium": count_medium,
            "findings_low": count_low,
        }

    except Exception as exc:
        db.rollback()
        try:
            from app.models.validation import RunStatus, ValidationRun

            run_q = db.query(ValidationRun).filter(ValidationRun.application_id == uuid.UUID(application_id)).order_by(ValidationRun.started_at.desc()).first()
            if run_q and run_q.status == RunStatus.RUNNING:
                run_q.status = RunStatus.FAILED
                run_q.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            db.rollback()
        if self is not None and hasattr(self, "retry"):
            raise self.retry(exc=exc)
        raise exc
    finally:
        db.close()


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name="app.tasks.validation_tasks.run_anomaly_detection",
)
def run_anomaly_detection(self, application_id: str) -> Dict[str, Any]:
    """Detect anomalies across all documents for an application.

    Checks performed:
    - Duplicate file hash detection (same document uploaded twice).
    - Documents where OCR failed (potential upload issue).
    - Mismatched detected document type vs declared type.

    Args:
        application_id: UUID string of the application.

    Returns:
        Dict with the count of anomalies flagged.
    """
    from app.models.anomaly import AnomalyFlag
    from app.models.audit import AuditLog
    from app.models.document import Document, OCRStatus

    db: Session = SyncSession()
    anomaly_count = 0

    try:
        app_uuid = uuid.UUID(application_id)
        documents: List[Document] = (
            db.query(Document).filter(Document.application_id == app_uuid).all()
        )

        # ── Duplicate hash check ──────────────────────────────────────────────
        hash_map: Dict[str, List[Document]] = {}
        for doc in documents:
            if doc.file_hash:
                hash_map.setdefault(doc.file_hash, []).append(doc)

        for file_hash, dupes in hash_map.items():
            if len(dupes) > 1:
                flag = AnomalyFlag(
                    application_id=app_uuid,
                    document_id=dupes[0].id,
                    check_type="DUPLICATE_DOCUMENT",
                    severity="HIGH",
                    confidence=0.99,
                    evidence=f"File hash {file_hash[:16]}… matched {len(dupes)} documents: "
                             + ", ".join(str(d.id) for d in dupes),
                    advisory_note="Multiple documents with identical content detected. Possible duplicate submission.",
                )
                db.add(flag)
                anomaly_count += 1

        # ── OCR failure check ─────────────────────────────────────────────────
        failed_docs = [d for d in documents if d.ocr_status == OCRStatus.FAILED]
        for doc in failed_docs:
            flag = AnomalyFlag(
                application_id=app_uuid,
                document_id=doc.id,
                check_type="OCR_FAILURE",
                severity="MEDIUM",
                confidence=1.0,
                evidence=f"Document {doc.id} ({doc.doc_type.value}) failed OCR processing.",
                advisory_note="Manual review of this document is recommended.",
            )
            db.add(flag)
            anomaly_count += 1

        # ── Type mismatch check ───────────────────────────────────────────────
        for doc in documents:
            if doc.extracted_data and doc.ocr_status == OCRStatus.COMPLETE:
                detected = doc.extracted_data.get("detected_doc_type", "")
                declared = doc.doc_type.value
                confidence = doc.extracted_data.get("classification_confidence", 1.0)
                if detected and detected != "UNKNOWN" and detected != declared and confidence > 0.5:
                    flag = AnomalyFlag(
                        application_id=app_uuid,
                        document_id=doc.id,
                        check_type="DOCUMENT_TYPE_MISMATCH",
                        severity="MEDIUM",
                        confidence=float(confidence),
                        evidence=(
                            f"Declared type: {declared}, "
                            f"AI-detected type: {detected} (confidence: {confidence:.2f})"
                        ),
                        advisory_note=(
                            "The document content does not match its declared category. "
                            "Please verify and re-upload the correct document."
                        ),
                    )
                    db.add(flag)
                    anomaly_count += 1

        audit = AuditLog(
            actor="SYSTEM",
            action="ANOMALY_DETECTION_COMPLETE",
            application_id=app_uuid,
            result=f"FLAGS:{anomaly_count}",
            notes=f"Anomaly detection complete. {anomaly_count} flag(s) raised.",
        )
        db.add(audit)
        db.commit()

        return {"application_id": application_id, "anomalies_flagged": anomaly_count}

    except Exception as exc:
        db.rollback()
        if self is not None and hasattr(self, "retry"):
            raise self.retry(exc=exc)
        raise exc
    finally:
        db.close()


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name="app.tasks.validation_tasks.run_verification",
)
def run_verification(self, application_id: str) -> Dict[str, Any]:
    """Verify documents against external / mock API sources.

    For each document that completed OCR, calls the mock API to verify
    reference numbers, NAAC grades, TER payments, etc.

    Args:
        application_id: UUID string of the application.

    Returns:
        Dict with verification result summary.
    """
    import httpx

    from app.models.audit import AuditLog
    from app.models.document import Document, DocumentType, OCRStatus
    from app.models.verification import VerificationResult, VerificationStatus

    db: Session = SyncSession()
    verified_count = 0
    failed_count = 0

    try:
        app_uuid = uuid.UUID(application_id)
        documents: List[Document] = (
            db.query(Document)
            .filter(
                Document.application_id == app_uuid,
                Document.ocr_status == OCRStatus.COMPLETE,
            )
            .all()
        )

        for doc in documents:
            fields = (doc.extracted_data or {}).get("fields", {})
            source_name: str
            payload: Dict[str, Any]
            endpoint: str

            # ── Route to appropriate verification endpoint ──────────────────
            if doc.doc_type == DocumentType.NAAC_CERT:
                source_name = "NAAC_API"
                endpoint = f"{settings.MOCK_API_BASE_URL}/verify/naac"
                payload = {
                    "institution_name": fields.get("institution_name", {}).get("value", ""),
                    "grade": fields.get("naac_grade", {}).get("value", ""),
                    "reference": (fields.get("reference_numbers", {}).get("value") or [""])[0],
                }
            elif doc.doc_type == DocumentType.TER_RECEIPT:
                source_name = "TER_API"
                endpoint = f"{settings.MOCK_API_BASE_URL}/verify/ter"
                payload = {
                    "institution_name": fields.get("institution_name", {}).get("value", ""),
                    "reference": (fields.get("reference_numbers", {}).get("value") or [""])[0],
                }
            elif doc.doc_type == DocumentType.AFFIDAVIT:
                source_name = "AFFIDAVIT_REGISTRY"
                endpoint = f"{settings.MOCK_API_BASE_URL}/verify/affidavit"
                payload = {
                    "reference": (fields.get("reference_numbers", {}).get("value") or [""])[0],
                }
            else:
                # For remaining doc types, record as VERIFICATION_PENDING
                vr = VerificationResult(
                    document_id=doc.id,
                    source_name="N/A",
                    status=VerificationStatus.VERIFICATION_PENDING,
                    source_response={"reason": "No automated verifier configured for this document type."},
                )
                db.add(vr)
                continue

            # ── Call mock API ─────────────────────────────────────────────────
            try:
                response = httpx.post(endpoint, json=payload, timeout=10.0)
                response_data: Dict[str, Any] = response.json()
                api_status: str = response_data.get("status", "UNKNOWN").upper()

                verification_status_map = {
                    "VERIFIED": VerificationStatus.VERIFIED,
                    "MISMATCH": VerificationStatus.MISMATCH_DETECTED,
                    "EXPIRED": VerificationStatus.EXPIRED,
                    "NOT_FOUND": VerificationStatus.MANUAL_REVIEW_REQUIRED,
                }
                ver_status = verification_status_map.get(
                    api_status, VerificationStatus.SOURCE_UNAVAILABLE
                )

                vr = VerificationResult(
                    document_id=doc.id,
                    source_name=source_name,
                    status=ver_status,
                    source_response=response_data,
                    reference_id=response_data.get("reference_id"),
                )
                db.add(vr)
                verified_count += 1

            except (httpx.RequestError, httpx.HTTPStatusError, Exception):
                vr = VerificationResult(
                    document_id=doc.id,
                    source_name=source_name,
                    status=VerificationStatus.SOURCE_UNAVAILABLE,
                    source_response={"error": "Could not reach verification source."},
                )
                db.add(vr)
                failed_count += 1

        audit = AuditLog(
            actor="SYSTEM",
            action="VERIFICATION_COMPLETE",
            application_id=app_uuid,
            result=f"VERIFIED:{verified_count},FAILED:{failed_count}",
            notes=f"Verification complete. {verified_count} succeeded, {failed_count} failed/unavailable.",
        )
        db.add(audit)
        db.commit()

        return {
            "application_id": application_id,
            "verified": verified_count,
            "source_unavailable": failed_count,
        }

    except Exception as exc:
        db.rollback()
        if self is not None and hasattr(self, "retry"):
            raise self.retry(exc=exc)
        raise exc
    finally:
        db.close()
