"""
scripts/seed_sqlite.py — Universal SQLAlchemy Demo Seeder
AICTE AI-Powered Application Validation Platform
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if not (backend_path / "app").exists():
    backend_path = Path("/app")
sys.path.insert(0, str(backend_path))

from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import hash_password
from app.models.institution import InstitutionRecord
from app.models.user import User, UserRole
from app.models.application import Application, ApplicationStatus, ApplicationType
from app.models.document import Document, DocumentType, OCRStatus
from app.models.validation import ValidationRun, ValidationFinding, RunStatus, FindingSeverity, FindingStatus
from app.models.anomaly import AnomalyFlag
from app.models.verification import VerificationResult, VerificationStatus
from app.models.audit import AuditLog
from app.models.alert import ApplicationAlert


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        from sqlalchemy import select
        existing = await session.execute(select(User).where(User.email == "officer@demo.com"))
        if existing.scalar_one_or_none():
            print("Database already seeded with demo accounts. Skipping.")
            return

        now = datetime.now(timezone.utc)

        # 1. Create Demo Institution Record
        inst_id = uuid.uuid4()
        inst = InstitutionRecord(
            id=inst_id,
            aicte_id="1-3324567891",
            name="ABC Institute of Technology & Engineering, Pune",
            state="Maharashtra",
            district="Pune",
            approved_intake=420,
            approved_programmes=["Computer Engineering", "Information Technology", "AI & Data Science", "Electronics & Telecom"],
            previous_eoa_status="APPROVED_2023_24",
            deficiency_history={"faculty_deficiency": 0, "infrastructure_deficiency": 0},
            ter_payment_status=True,
            naac_grade="A+",
            created_at=now,
        )
        session.add(inst)

        # 2. Create Users
        demo_pwd = hash_password("Demo@1234")

        user_inst = User(
            id=uuid.uuid4(),
            email="institution@demo.com",
            full_name="Dr. Ramesh Kulkarni (Principal)",
            role=UserRole.INSTITUTION,
            hashed_password=demo_pwd,
            institution_id=inst_id,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        user_officer = User(
            id=uuid.uuid4(),
            email="officer@demo.com",
            full_name="Shri Alok Kumar (Scrutiny Officer)",
            role=UserRole.OFFICER,
            hashed_password=demo_pwd,
            institution_id=None,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        user_senior = User(
            id=uuid.uuid4(),
            email="senior@demo.com",
            full_name="Dr. Sunita Sharma (Regional Officer)",
            role=UserRole.SENIOR_OFFICER,
            hashed_password=demo_pwd,
            institution_id=None,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        user_officer_aicte = User(
            id=uuid.uuid4(),
            email="officer@aicte.gov.in",
            full_name="Shri Alok Kumar (Scrutiny Officer)",
            role=UserRole.OFFICER,
            hashed_password=demo_pwd,
            institution_id=None,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        user_reg_bvcoe = User(
            id=uuid.uuid4(),
            email="registrar@bvcoe.edu.in",
            full_name="Dr. Ramesh Kulkarni (Principal)",
            role=UserRole.INSTITUTION,
            hashed_password=demo_pwd,
            institution_id=inst_id,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add_all([user_inst, user_officer, user_senior, user_officer_aicte, user_reg_bvcoe])

        # 3. Create 8 Demo Applications
        scenarios = [
            ("APP-2024-001", "ABC Institute of Technology & Engineering, Pune", ApplicationStatus.APPROVED_FOR_PROCESSING, 95, "Fully Valid Application (Auto-verification verified all records)"),
            ("APP-2024-002", "Shri Shivaji Technical College, Nagpur", ApplicationStatus.UNDER_REVIEW, 68, "Expired Fire Safety NOC (Requires Inspection)"),
            ("APP-2024-003", "Vidya Pratishthan College of Engineering, Baramati", ApplicationStatus.SENT_FOR_RECTIFICATION, 52, "Missing Mandatory State Government NOC"),
            ("APP-2024-004", "Marathwada Institute of Technology, Aurangabad", ApplicationStatus.UNDER_VALIDATION, 82, "Cross-Document Name Inconsistency Alert"),
            ("APP-2024-005", "K. J. Somaiya College of Engineering, Mumbai", ApplicationStatus.VALIDATION_COMPLETE, 88, "Metadata Creation Date Anomaly Flagged"),
            ("APP-2024-006", "Sinhgad Academy of Engineering, Kondhwa", ApplicationStatus.ESCALATED, 45, "Source Verification Mismatch (NAAC Portal Mismatch)"),
            ("APP-2024-007", "D. Y. Patil Institute of Technology, Pimpri", ApplicationStatus.SUBMITTED, None, "Newly Submitted — Queued for AI Scrutiny"),
            ("APP-2024-008", "Government Polytechnic, Kolhapur", ApplicationStatus.DRAFT, None, "Draft Application — Incomplete Uploads"),
        ]

        doc_types = [
            DocumentType.AFFIDAVIT,
            DocumentType.STATE_NOC,
            DocumentType.NAAC_CERT,
            DocumentType.FIRE_SAFETY_CERT,
            DocumentType.TER_RECEIPT,
            DocumentType.LAND_BUILDING_DOC,
            DocumentType.FACULTY_DATA,
            DocumentType.EOA_FORM,
        ]

        for code, inst_name, app_status, score, scenario_desc in scenarios:
            app_id = uuid.uuid4()
            app = Application(
                id=app_id,
                institution_id=inst_id,
                institution_name=inst_name,
                application_type=ApplicationType.EOA_RENEWAL,
                status=app_status,
                academic_year="2024-25",
                programmes=["Computer Engineering", "Information Technology", "AI & Data Science"],
                submitted_at=now - timedelta(days=2) if app_status != ApplicationStatus.DRAFT else None,
                created_at=now - timedelta(days=5),
                updated_at=now,
            )
            session.add(app)

            # Add documents for this application
            docs_to_add = doc_types if app_status != ApplicationStatus.DRAFT else doc_types[:4]
            created_docs = []
            for dt in docs_to_add:
                doc_id = uuid.uuid4()
                ref_num = f"VALID-{uuid.uuid4().hex[:8].upper()}" if score and score > 80 else f"EXP-{uuid.uuid4().hex[:8].upper()}"
                doc = Document(
                    id=doc_id,
                    application_id=app_id,
                    doc_type=dt,
                    file_path=f"applications/{app_id}/{dt.value}/sample_{dt.value.lower()}.pdf",
                    file_name=f"{dt.value.lower()}_2024.pdf",
                    file_size=245800,
                    mime_type="application/pdf",
                    ocr_status=OCRStatus.COMPLETE,
                    extracted_data={
                        "confidence": 0.94,
                        "fields": {
                            "institution_name": {"value": inst_name, "confidence": 0.96},
                            "approval_number": {"value": "AICTE-WRO-2024-88912", "confidence": 0.92},
                            "reference_numbers": {"value": [ref_num], "confidence": 0.95},
                            "dates": ["15/06/2024", "31/12/2025"],
                        }
                    },
                    file_hash=uuid.uuid4().hex * 2,
                    uploaded_at=now - timedelta(days=3),
                    updated_at=now - timedelta(days=3),
                )
                session.add(doc)
                created_docs.append(doc)

            # If scored, create validation run and findings
            if score is not None:
                run_id = uuid.uuid4()
                run = ValidationRun(
                    id=run_id,
                    application_id=app_id,
                    started_at=now - timedelta(hours=4),
                    completed_at=now - timedelta(hours=3, minutes=58),
                    overall_score=score,
                    status=RunStatus.COMPLETE,
                    rules_version="2024.1.0",
                    findings_count_high=0 if score >= 85 else (2 if score < 60 else 1),
                    findings_count_medium=1 if score < 90 else 0,
                    findings_count_low=1,
                )
                session.add(run)

                # Add sample findings
                finding1 = ValidationFinding(
                    id=uuid.uuid4(),
                    validation_run_id=run_id,
                    rule_id="R001",
                    rule_name="Affidavit Mandatory Presence",
                    severity=FindingSeverity.HIGH,
                    status=FindingStatus.PASS if score >= 60 else FindingStatus.FAIL,
                    document_id=created_docs[0].id if created_docs else None,
                    evidence=f"Affidavit verified under notary registration for {inst_name}",
                    message="Mandatory institutional affidavit verified.",
                    category="COMPLETENESS",
                )
                finding2 = ValidationFinding(
                    id=uuid.uuid4(),
                    validation_run_id=run_id,
                    rule_id="R009",
                    rule_name="State NOC Validity",
                    severity=FindingSeverity.HIGH,
                    status=FindingStatus.PASS if score >= 80 else FindingStatus.FAIL,
                    document_id=created_docs[1].id if len(created_docs) > 1 else None,
                    evidence="NOC validity checked against Maharashtra DTE records.",
                    message="State Government No-Objection Certificate valid.",
                    category="VALIDITY",
                )
                finding3 = ValidationFinding(
                    id=uuid.uuid4(),
                    validation_run_id=run_id,
                    rule_id="R013",
                    rule_name="NAAC Grade Threshold",
                    severity=FindingSeverity.MEDIUM,
                    status=FindingStatus.PASS,
                    document_id=created_docs[2].id if len(created_docs) > 2 else None,
                    evidence="Extracted NAAC grade: A+ | Meets threshold >= B+",
                    message="NAAC accreditation threshold fulfilled.",
                    category="COMPLIANCE",
                )
                session.add_all([finding1, finding2, finding3])

                # Add anomaly flag if scenario warrants
                if "Anomaly" in scenario_desc or "Inconsistency" in scenario_desc:
                    anom = AnomalyFlag(
                        id=uuid.uuid4(),
                        application_id=app_id,
                        document_id=created_docs[0].id,
                        check_type="METADATA_CREATION_DATE_MISMATCH",
                        severity="HIGH",
                        confidence=0.88,
                        evidence="PDF metadata creation timestamp (2018) precedes stated issuance year (2024) by 6 years.",
                        advisory_note="Preliminary flag for scrutiny officer review. Verify original document stamp.",
                        created_at=now,
                        is_reviewed=False,
                    )
                    session.add(anom)

                # Add verification result
                ver_res = VerificationResult(
                    id=uuid.uuid4(),
                    document_id=created_docs[0].id,
                    source_name="State Judicial Registry",
                    status=VerificationStatus.VERIFIED if score >= 70 else VerificationStatus.MISMATCH_DETECTED,
                    source_response={"status": "VERIFIED", "source": "DigiLocker / State Judicial"},
                    reference_id=f"NOTARY-2024-{code}",
                    verified_at=now - timedelta(hours=3),
                )
                session.add(ver_res)

            # Audit log
            audit = AuditLog(
                id=uuid.uuid4(),
                event_id=uuid.uuid4(),
                timestamp=now - timedelta(days=2),
                actor="SYSTEM",
                action="SEEDED_DEMO_SCENARIO",
                application_id=app_id,
                result="SUCCESS",
                notes=scenario_desc,
            )
            session.add(audit)

        await session.commit()
        print("Demo database successfully seeded with:")
        print(" - 1 Institution Record")
        print(" - 3 Demo Users (institution@demo.com, officer@demo.com, senior@demo.com)")
        print(" - 8 Application scenarios with documents, findings, anomalies, and verification results.")

if __name__ == "__main__":
    asyncio.run(seed())
