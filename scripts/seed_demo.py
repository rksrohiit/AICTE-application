#!/usr/bin/env python3
"""
scripts/seed_demo.py
====================
Seeds the AICTE Validation Platform database with demo data for development
and hackathon demonstration purposes.

Creates:
  - 3 demo users (institution, scrutiny officer, senior officer)
  - 1 demo InstitutionRecord (ABC Institute of Technology, Maharashtra)
  - 8 demo applications covering varied validation scenarios
  - Document records with realistic extracted_data JSON for each application

Usage:
    python scripts/seed_demo.py

    Or inside Docker:
    docker compose exec backend python /app/scripts/seed_demo.py

Reads DATABASE_URL from backend/.env (falls back to hardcoded dev default).
"""

import os
import sys
import json
import uuid
import hmac
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

# ─── Try to load DATABASE_URL from .env ──────────────────────────────────────
def _load_env(env_path: Path) -> dict:
    env_vars = {}
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env_vars[k.strip()] = v.strip().strip('"').strip("'")
    return env_vars


_SCRIPT_DIR = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_ENV_PATH = _PROJECT_ROOT / "backend" / ".env"
_ENV = _load_env(_ENV_PATH)

DATABASE_URL = (
    _ENV.get("DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or "postgresql://aicte:aicte_secret@localhost:5432/aicte_db"
)

# Strip async prefix if present (psycopg2 needs sync URL)
DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace(
    "postgresql+psycopg2://", "postgresql://"
)

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    from app.core.security import hash_password
except ImportError:
    print(
        "ERROR: psycopg2 not installed. Run: pip install psycopg2-binary",
        file=sys.stderr,
    )
    sys.exit(1)


# ─── Password hashing ─────────────────────────────────────────────────────────
def _hash_password(plain: str) -> str:
    """Hash demo credentials with the same bcrypt strategy as login."""
    return hash_password(plain)


DEMO_PASSWORD_HASH = _hash_password("Demo@1234")

# ─── Demo data definitions ────────────────────────────────────────────────────

TODAY = date.today()

DEMO_USERS = [
    {
        "id": str(uuid.uuid4()),
        "email": "institution@demo.com",
        "full_name": "Dr. Ramesh Kulkarni",
        "role": "INSTITUTION",
        "hashed_password": DEMO_PASSWORD_HASH,
        "is_active": True,
        "created_at": datetime.utcnow(),
    },
    {
        "id": str(uuid.uuid4()),
        "email": "officer@demo.com",
        "full_name": "Ms. Priya Sharma",
        "role": "SCRUTINY_OFFICER",
        "hashed_password": DEMO_PASSWORD_HASH,
        "is_active": True,
        "created_at": datetime.utcnow(),
    },
    {
        "id": str(uuid.uuid4()),
        "email": "senior@demo.com",
        "full_name": "Mr. Anil Mehta",
        "role": "SENIOR_OFFICER",
        "hashed_password": DEMO_PASSWORD_HASH,
        "is_active": True,
        "created_at": datetime.utcnow(),
    },
]

INSTITUTION_ID = str(uuid.uuid4())

DEMO_INSTITUTION = {
    "id": INSTITUTION_ID,
    "name": "ABC Institute of Technology",
    "short_name": "ABCIT",
    "aicte_id": "AICTE-MH-2010-00421",
    "state": "Maharashtra",
    "district": "Pune",
    "city": "Pune",
    "pincode": "411041",
    "address": "Plot No. 42, Sector 7, MIDC, Chinchwad, Pune - 411041",
    "institute_type": "Private",
    "affiliated_university": "Savitribai Phule Pune University",
    "established_year": 2010,
    "contact_email": "principal@abcit.edu.in",
    "contact_phone": "020-27412345",
    "website": "https://www.abcit.edu.in",
    "created_at": datetime.utcnow(),
}

# ─── 8 demo applications with varied scenarios ────────────────────────────────

def _make_app(idx: int, institution_user_id: str, scenario: dict) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "institution_id": INSTITUTION_ID,
        "submitted_by": institution_user_id,
        "application_type": scenario.get("app_type", "EOA_RENEWAL"),
        "academic_year": "2024-25",
        "status": scenario["status"],
        "ai_validation_score": scenario.get("score"),
        "flags_count": scenario.get("flags", 0),
        "remarks": scenario.get("remarks", ""),
        "submitted_at": datetime.utcnow() - timedelta(days=scenario.get("days_ago", 1)),
        "created_at": datetime.utcnow() - timedelta(days=scenario.get("days_ago", 1)),
    }


APPLICATION_SCENARIOS = [
    {
        "label": "All documents valid — auto-approved candidate",
        "status": "UNDER_REVIEW",
        "score": 97.5,
        "flags": 0,
        "remarks": "All 22 rules passed. Recommended for auto-approval.",
        "days_ago": 2,
        "app_type": "EOA_RENEWAL",
    },
    {
        "label": "Expired fire safety certificate",
        "status": "FLAGGED",
        "score": 72.0,
        "flags": 1,
        "remarks": "R011: Fire Safety Certificate expired 45 days ago.",
        "days_ago": 5,
        "app_type": "EOA_RENEWAL",
    },
    {
        "label": "Missing NAAC certificate",
        "status": "FLAGGED",
        "score": 65.0,
        "flags": 2,
        "remarks": "R003: NAAC certificate not uploaded. R012: NAAC validity check skipped.",
        "days_ago": 3,
        "app_type": "EOA_RENEWAL",
    },
    {
        "label": "Institution name mismatch across documents",
        "status": "FLAGGED",
        "score": 80.0,
        "flags": 1,
        "remarks": "R017: Institution name on State NOC ('ABC Inst. of Tech') does not match EOA form ('ABC Institute of Technology').",
        "days_ago": 7,
        "app_type": "EOA_RENEWAL",
    },
    {
        "label": "TER payment pending",
        "status": "RETURNED",
        "score": 60.0,
        "flags": 3,
        "remarks": "R020: TER payment status is PENDING. Application returned for compliance.",
        "days_ago": 10,
        "app_type": "EOA_RENEWAL",
    },
    {
        "label": "Faculty qualification ratio below threshold",
        "status": "UNDER_REVIEW",
        "score": 85.0,
        "flags": 1,
        "remarks": "R021: Only 15% faculty hold Ph.D. (minimum 20% required).",
        "days_ago": 1,
        "app_type": "EOA_RENEWAL",
    },
    {
        "label": "New programme application — all docs present",
        "status": "APPROVED",
        "score": 95.0,
        "flags": 0,
        "remarks": "All rules passed. Approved by senior officer.",
        "days_ago": 30,
        "app_type": "NEW_PROGRAMME",
    },
    {
        "label": "Multiple issues — OCR failure on one document",
        "status": "DRAFT",
        "score": None,
        "flags": 0,
        "remarks": "CMN004: OCR failed on uploaded Land Building document (image too blurry).",
        "days_ago": 0,
        "app_type": "EOA_RENEWAL",
    },
]

# ─── Document records with extracted_data ─────────────────────────────────────

DOC_TYPES = [
    "AFFIDAVIT",
    "STATE_NOC",
    "NAAC_CERT",
    "FIRE_SAFETY_CERT",
    "TER_RECEIPT",
    "LAND_BUILDING_DOC",
    "FACULTY_DATA",
    "EOA_FORM",
]


def _make_extracted_data(doc_type: str, scenario_idx: int) -> dict:
    """Generate realistic extracted_data JSON for each document type."""
    base = {
        "institution_name": "ABC Institute of Technology",
        "approval_number": "WEST-2024-00421",
        "extraction_confidence": 0.94,
        "ocr_status": "SUCCESS",
    }

    if doc_type == "AFFIDAVIT":
        base.update({
            "affiant_name": "Dr. Ramesh Kulkarni",
            "designation": "Principal",
            "issue_date": (TODAY - timedelta(days=30)).isoformat(),
            "notary_name": "Adv. Sanjay Patil",
            "notary_registration": "MH/PUN/2015/0042",
        })

    elif doc_type == "STATE_NOC":
        valid_till = (TODAY + timedelta(days=180)).isoformat()
        if scenario_idx == 3:  # Name mismatch scenario
            base["institution_name"] = "ABC Inst. of Tech"
        base.update({
            "noc_number": "DTE/NOC/2024/0421",
            "issued_by": "Director of Technical Education, Maharashtra",
            "issue_date": (TODAY - timedelta(days=60)).isoformat(),
            "valid_till": valid_till,
            "state": "Maharashtra",
            "approved_intake": 120,
        })

    elif doc_type == "NAAC_CERT":
        if scenario_idx == 2:  # Missing NAAC scenario — mark as not uploaded
            return {"ocr_status": "NOT_UPLOADED", "extraction_confidence": 0.0}
        base.update({
            "cert_no": "NAAC/CERT/2022/MH/4521",
            "grade": "A+",
            "cgpa": 3.42,
            "cycle": "3rd",
            "valid_till": (TODAY + timedelta(days=365 * 4)).isoformat(),
            "peer_team_visit_date": "2022-03-15",
        })

    elif doc_type == "FIRE_SAFETY_CERT":
        if scenario_idx == 1:  # Expired fire safety scenario
            base.update({
                "cert_no": "FIRE/PUN/2023/0891",
                "issued_by": "Pune District Fire Officer",
                "issue_date": (TODAY - timedelta(days=400)).isoformat(),
                "valid_till": (TODAY - timedelta(days=45)).isoformat(),  # Expired
                "building_type": "Educational Institution",
            })
        else:
            base.update({
                "cert_no": "FIRE/PUN/2024/0334",
                "issued_by": "Pune District Fire Officer",
                "issue_date": (TODAY - timedelta(days=30)).isoformat(),
                "valid_till": (TODAY + timedelta(days=335)).isoformat(),
                "building_type": "Educational Institution",
            })

    elif doc_type == "TER_RECEIPT":
        payment_status = "PENDING" if scenario_idx == 4 else "PAID"
        base.update({
            "receipt_no": f"TER/2024/{1000 + scenario_idx}",
            "payment_status": payment_status,
            "amount_paid": 0 if payment_status == "PENDING" else 250000,
            "payment_date": None if payment_status == "PENDING" else (TODAY - timedelta(days=15)).isoformat(),
            "bank_reference": None if payment_status == "PENDING" else "HDFC20240315001",
        })

    elif doc_type == "LAND_BUILDING_DOC":
        if scenario_idx == 7:  # OCR failure scenario
            base.update({
                "ocr_status": "FAILED",
                "extraction_confidence": 0.0,
                "failure_reason": "Image resolution too low for OCR (< 150 DPI)",
            })
        else:
            base.update({
                "doc_type": "Sale Deed",
                "land_area_sqm": 8500,
                "building_area_sqm": 3200,
                "survey_number": "123/A/4",
                "owner_name": "ABC Education Trust",
                "registration_number": "MH/REG/PUN/2009/4521",
            })

    elif doc_type == "FACULTY_DATA":
        phd_count = 4 if scenario_idx == 5 else 12  # Ratio issue on scenario 5
        total_count = 28
        base.update({
            "total_faculty_count": total_count,
            "permanent_faculty": 20,
            "visiting_faculty": 8,
            "phd_faculty_count": phd_count,
            "mtech_faculty_count": 14,
            "faculty_student_ratio": "1:15",
            "female_faculty_count": 10,
        })

    elif doc_type == "EOA_FORM":
        base.update({
            "form_version": "EOA-2024-v3",
            "programme_name": "B.Tech Computer Engineering",
            "approved_intake": 120,
            "existing_intake": 120,
            "signature_present": True,
            "date_of_submission": TODAY.isoformat(),
            "contact_email": "principal@abcit.edu.in",
            "contact_phone": "020-27412345",
        })

    return base


def _make_documents(app_id: str, scenario_idx: int) -> list[dict]:
    docs = []
    for doc_type in DOC_TYPES:
        extracted = _make_extracted_data(doc_type, scenario_idx)
        ocr_ok = extracted.get("ocr_status", "SUCCESS") == "SUCCESS"
        docs.append({
            "id": str(uuid.uuid4()),
            "application_id": app_id,
            "document_type": doc_type,
            "original_filename": f"{doc_type.lower()}_{scenario_idx + 1}.pdf",
            "storage_path": f"applications/{app_id}/{doc_type.lower()}.pdf",
            "file_size_bytes": 512000 + (scenario_idx * 10000),
            "mime_type": "application/pdf",
            "ocr_status": extracted.get("ocr_status", "SUCCESS"),
            "extraction_confidence": extracted.get("extraction_confidence", 0.94),
            "extracted_data": json.dumps(extracted),
            "uploaded_at": datetime.utcnow() - timedelta(days=scenario_idx),
            "created_at": datetime.utcnow() - timedelta(days=scenario_idx),
        })
    return docs


# ─── DB helpers ──────────────────────────────────────────────────────────────

def _execute(conn, sql: str, params: tuple = ()):
    with conn.cursor() as cur:
        cur.execute(sql, params)


def _upsert_user(conn, user: dict):
    sql = """
        INSERT INTO users (id, email, full_name, role, hashed_password, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (email) DO UPDATE
          SET full_name = EXCLUDED.full_name,
              hashed_password = EXCLUDED.hashed_password,
              role = EXCLUDED.role,
              is_active = EXCLUDED.is_active,
              updated_at = EXCLUDED.updated_at;
    """
    now = datetime.utcnow()
    _execute(conn, sql, (
        user["id"], user["email"], user["full_name"], user["role"],
        user["hashed_password"], user["is_active"], user["created_at"], now,
    ))


def _upsert_institution(conn, inst: dict):
    sql = """
        INSERT INTO institutions (
            id, name, short_name, aicte_id, state, district, city, pincode,
            address, institute_type, affiliated_university, established_year,
            contact_email, contact_phone, website, created_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (aicte_id) DO UPDATE
          SET name = EXCLUDED.name,
              state = EXCLUDED.state;
    """
    _execute(conn, sql, (
        inst["id"], inst["name"], inst["short_name"], inst["aicte_id"],
        inst["state"], inst["district"], inst["city"], inst["pincode"],
        inst["address"], inst["institute_type"], inst["affiliated_university"],
        inst["established_year"], inst["contact_email"], inst["contact_phone"],
        inst["website"], inst["created_at"],
    ))


def _insert_application(conn, app: dict):
    sql = """
        INSERT INTO applications (
            id, institution_id, submitted_by, application_type, academic_year,
            status, ai_validation_score, flags_count, remarks, submitted_at, created_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO NOTHING;
    """
    _execute(conn, sql, (
        app["id"], app["institution_id"], app["submitted_by"],
        app["application_type"], app["academic_year"], app["status"],
        app["ai_validation_score"], app["flags_count"], app["remarks"],
        app["submitted_at"], app["created_at"],
    ))


def _insert_document(conn, doc: dict):
    sql = """
        INSERT INTO documents (
            id, application_id, document_type, original_filename, storage_path,
            file_size_bytes, mime_type, ocr_status, extraction_confidence,
            extracted_data, uploaded_at, created_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO NOTHING;
    """
    _execute(conn, sql, (
        doc["id"], doc["application_id"], doc["document_type"],
        doc["original_filename"], doc["storage_path"], doc["file_size_bytes"],
        doc["mime_type"], doc["ocr_status"], doc["extraction_confidence"],
        doc["extracted_data"], doc["uploaded_at"], doc["created_at"],
    ))


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  AICTE Validation Platform — Demo Data Seeder")
    print("=" * 65)
    print(f"\nConnecting to: {DATABASE_URL}")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
    except Exception as e:
        print(f"\n❌ Could not connect to database: {e}", file=sys.stderr)
        print("   Make sure PostgreSQL is running and DATABASE_URL is correct.", file=sys.stderr)
        sys.exit(1)

    print("✅ Connected.\n")

    institution_user_id = DEMO_USERS[0]["id"]

    try:
        # 1. Seed users
        print("📋 Seeding demo users…")
        for user in DEMO_USERS:
            _upsert_user(conn, user)
            print(f"   ✓ {user['role']:20s} → {user['email']}")

        # 2. Seed institution
        print("\n🏫 Seeding demo institution…")
        _upsert_institution(conn, DEMO_INSTITUTION)
        print(f"   ✓ {DEMO_INSTITUTION['name']} ({DEMO_INSTITUTION['aicte_id']})")

        # 3. Seed applications + documents
        print("\n📂 Seeding demo applications and documents…")
        total_docs = 0
        for idx, scenario in enumerate(APPLICATION_SCENARIOS):
            app = _make_app(idx, institution_user_id, scenario)
            _insert_application(conn, app)
            docs = _make_documents(app["id"], idx)
            for doc in docs:
                _insert_document(conn, doc)
            total_docs += len(docs)
            print(
                f"   [{idx + 1}/8] {scenario['status']:14s}  score={str(scenario.get('score') or 'N/A'):6s}  "
                f"flags={scenario['flags']}  → {scenario['label']}"
            )

        conn.commit()
        print("\n✅ All demo data committed successfully.")
        print(f"\nSummary:")
        print(f"  Users created/updated : {len(DEMO_USERS)}")
        print(f"  Institutions          : 1")
        print(f"  Applications          : {len(APPLICATION_SCENARIOS)}")
        print(f"  Document records      : {total_docs}")
        print(f"\n{'─' * 65}")
        print("  Demo login credentials (all passwords: Demo@1234)")
        print(f"{'─' * 65}")
        for user in DEMO_USERS:
            print(f"  {user['role']:20s} → {user['email']}")
        print(f"{'─' * 65}\n")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error during seeding: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
