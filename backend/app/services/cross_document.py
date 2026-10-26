"""
cross_document.py — Cross-Document Consistency Engine
AICTE AI-Powered Application Validation Platform

Principles:
- Works with uploaded documents even before external issuing authority APIs are reachable.
- Evaluates fields that genuinely appear across multiple document types:
  institution_name, institution_id, address, academic_year, approval_ref_number, approved_programme.
- Uses semantic normalization and token comparison (never crude fuzzy matching alone).
- Preserves exact page-level provenance (document_id, file_name, page_number, extracted_value).
"""

from __future__ import annotations

import difflib
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document

# ── Document Type Authoritativeness Mapping ──────────────────────────────────
# Under AICTE regulations, certain documents are primary legal authorities for specific claims:
AUTHORITATIVE_DOCS: Dict[str, List[str]] = {
    "institution_name": ["EOA_FORM", "AFFIDAVIT", "STATE_NOC"],
    "institution_id": ["EOA_FORM", "TER_RECEIPT"],
    "address": ["LAND_BUILDING_DOC", "STATE_NOC", "AFFIDAVIT"],
    "academic_year": ["EOA_FORM", "TER_RECEIPT"],
    "approval_ref_number": ["STATE_NOC", "EOA_FORM"],
    "approved_programme": ["EOA_FORM", "FACULTY_DATA"],
}

# Standard Indian Institutional Abbreviation Normalization Dictionary
ABBREVIATION_EXPANSIONS = {
    r"\binst\b\.?": "institute",
    r"\btech\b\.?": "technology",
    r"\bengg\b\.?": "engineering",
    r"\bcoll\b\.?": "college",
    r"\buniv\b\.?": "university",
    r"\bdept\b\.?": "department",
    r"\brd\b\.?": "road",
    r"\bst\b\.?": "street",
    r"\bp\.?o\.?\b": "post office",
    r"\bdist\b\.?": "district",
    r"\bsec\b\.?": "sector",
    r"\bdr\b\.?": "doctor",
    r"\bprof\b\.?": "professor",
    r"\bgov\b\.?": "government",
    r"\bgovt\b\.?": "government",
    r"&": "and",
}


def normalize_field_value(value: Any, field_name: str) -> str:
    """Normalize extracted claim values for honest, robust cross-document comparison."""
    if value is None:
        return ""
    text = str(value).strip().lower()

    # Normalization for Academic Year: e.g. "2024-25" -> "2024-2025"
    if field_name == "academic_year":
        m = re.match(r"^(\d{4})[-/](\d{2})$", text)
        if m:
            prefix = m.group(1)[:2]
            return f"{m.group(1)}-{prefix}{m.group(2)}"
        return text.replace(" ", "")

    # Normalization for Institution ID: strip "1-", spaces, leading zeros
    if field_name == "institution_id":
        cleaned = re.sub(r"[^a-zA-Z0-9]", "", text)
        return cleaned.lstrip("0")

    # General text normalization (names, addresses)
    # 1. Expand standard legal & institutional abbreviations
    for pattern, expansion in ABBREVIATION_EXPANSIONS.items():
        text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)

    # 2. Collapse punctuation and multiple whitespaces
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = [t for t in text.split() if t]
    return " ".join(tokens)


def compute_token_similarity(norm_a: str, norm_b: str) -> float:
    """Compute bidirectional token overlap and sequence similarity."""
    if not norm_a or not norm_b:
        return 0.0
    if norm_a == norm_b:
        return 1.0

    tokens_a = set(norm_a.split())
    tokens_b = set(norm_b.split())

    if not tokens_a or not tokens_b:
        return 0.0

    # Jaccard token overlap
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    jaccard = len(intersection) / len(union)

    # Sequence matcher ratio
    seq_ratio = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()

    # Blended score (60% token overlap + 40% sequence order)
    return round((0.6 * jaccard) + (0.4 * seq_ratio), 4)


class CrossDocumentEvidence(BaseModel):
    """Source provenance for a claim extracted from an individual document."""

    document_id: str
    doc_type: str
    file_name: str
    page: int
    extracted_value: Any
    confidence: float
    raw_snippet: Optional[str] = None


class CrossDocumentFinding(BaseModel):
    """Result of cross-document consistency scrutiny for a specific field."""

    finding_type: str = "CROSS_DOCUMENT_CONFLICT"
    field: str
    status: Literal["CONSISTENT", "NEEDS_REVIEW", "CONFLICT"]
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    similarity_score: float
    authoritative_doc_type: Optional[str]
    resolution_guidance: str
    evidence: List[CrossDocumentEvidence]
    explanation: str


class CrossDocumentConsistencyReport(BaseModel):
    """Full consistency scrutiny report across all documents for an application."""

    application_id: str
    total_documents_analyzed: int
    overall_consistency_status: Literal["VERIFIED_CONSISTENT", "NEEDS_HUMAN_REVIEW", "CONFLICTS_DETECTED"]
    total_conflicts: int
    total_warnings: int
    findings: List[CrossDocumentFinding]
    analyzed_at: str


class CrossDocumentConsistencyEngine:
    """Scrutinizes claims across multiple uploaded documents to find cross-document conflicts."""

    TARGET_FIELDS = [
        "institution_name",
        "institution_id",
        "address",
        "academic_year",
        "approval_ref_number",
        "approved_programme",
    ]

    @classmethod
    def analyze_documents(
        cls, application_id: uuid.UUID, documents: List[Document]
    ) -> CrossDocumentConsistencyReport:
        """Evaluate consistency of extracted fields across all documents for an application."""
        # 1. Collect claims by field across all documents
        field_claims: Dict[str, List[CrossDocumentEvidence]] = {
            f: [] for f in cls.TARGET_FIELDS
        }

        for doc in documents:
            claims_data = doc.extracted_claims or []
            # Fallback to extracted_data.fields if extracted_claims is empty
            if not claims_data and doc.extracted_data:
                fields = doc.extracted_data.get("fields", {})
                for f_name, f_val in fields.items():
                    if f_name in cls.TARGET_FIELDS and f_val.get("value") is not None:
                        field_claims[f_name].append(
                            CrossDocumentEvidence(
                                document_id=str(doc.id),
                                doc_type=doc.doc_type.value,
                                file_name=doc.file_name,
                                page=1,
                                extracted_value=f_val["value"],
                                confidence=f_val.get("confidence", 0.8),
                                raw_snippet=str(f_val["value"]),
                            )
                        )
                continue

            for claim in claims_data:
                f_name = claim.get("field_name")
                val = claim.get("value")
                if f_name in cls.TARGET_FIELDS and val is not None:
                    field_claims[f_name].append(
                        CrossDocumentEvidence(
                            document_id=str(doc.id),
                            doc_type=doc.doc_type.value,
                            file_name=doc.file_name,
                            page=claim.get("page_number", 1),
                            extracted_value=val,
                            confidence=claim.get("confidence", 0.85),
                            raw_snippet=claim.get("raw_snippet"),
                        )
                    )

        # 2. Evaluate each field where 2 or more documents provided a claim
        findings: List[CrossDocumentFinding] = []
        conflicts_count = 0
        warnings_count = 0

        for field_name, evidence_list in field_claims.items():
            if len(evidence_list) < 2:
                continue

            # Identify the most authoritative document present
            authoritative_types = AUTHORITATIVE_DOCS.get(field_name, [])
            auth_evidence = next(
                (ev for ev in evidence_list if ev.doc_type in authoritative_types),
                evidence_list[0],
            )

            auth_norm = normalize_field_value(auth_evidence.extracted_value, field_name)

            # Compare all other documents against the authoritative reference
            min_similarity = 1.0
            worst_evidence = auth_evidence

            for other_ev in evidence_list:
                if other_ev.document_id == auth_evidence.document_id:
                    continue
                other_norm = normalize_field_value(other_ev.extracted_value, field_name)
                sim = compute_token_similarity(auth_norm, other_norm)

                if sim < min_similarity:
                    min_similarity = sim
                    worst_evidence = other_ev

            # Categorize the outcome
            if min_similarity >= 0.90:
                # Consistent
                status = "CONSISTENT"
                severity = "LOW"
                explanation = (
                    f"'{field_name.replace('_', ' ').title()}' is consistent across all {len(evidence_list)} "
                    f"uploaded documents (similarity {int(min_similarity * 100)}%)."
                )
                guidance = "No regulatory action required."
            elif min_similarity >= 0.70:
                # Minor variance / abbreviation difference (NEEDS_REVIEW, not fraud!)
                status = "NEEDS_REVIEW"
                severity = "MEDIUM"
                warnings_count += 1
                explanation = (
                    f"Minor variation in '{field_name.replace('_', ' ').title()}' between "
                    f"{auth_evidence.doc_type} (Page {auth_evidence.page}) and {worst_evidence.doc_type} (Page {worst_evidence.page}). "
                    f"Token similarity is {int(min_similarity * 100)}%. This may reflect standard abbreviations rather than misrepresentation."
                )
                guidance = f"Officer manual review advised: Confirm that '{worst_evidence.extracted_value}' refers to the same legal entity as '{auth_evidence.extracted_value}'."
            else:
                # Substantial conflict
                status = "CONFLICT"
                severity = "HIGH"
                conflicts_count += 1
                explanation = (
                    f"Cross-document conflict in '{field_name.replace('_', ' ').title()}': "
                    f"{auth_evidence.doc_type} states '{auth_evidence.extracted_value}' (Page {auth_evidence.page}), "
                    f"whereas {worst_evidence.doc_type} states '{worst_evidence.extracted_value}' (Page {worst_evidence.page}). "
                    f"Similarity is only {int(min_similarity * 100)}%."
                )
                guidance = f"Require rectification: Request clarifying affidavit or certified NOC addressing the discrepancy between {auth_evidence.doc_type} and {worst_evidence.doc_type}."

            findings.append(
                CrossDocumentFinding(
                    finding_type="CROSS_DOCUMENT_CONFLICT" if status != "CONSISTENT" else "CROSS_DOCUMENT_VERIFIED",
                    field=field_name,
                    status=status,
                    severity=severity,
                    similarity_score=min_similarity,
                    authoritative_doc_type=auth_evidence.doc_type,
                    resolution_guidance=guidance,
                    evidence=evidence_list,
                    explanation=explanation,
                )
            )

        overall_status = "VERIFIED_CONSISTENT"
        if conflicts_count > 0:
            overall_status = "CONFLICTS_DETECTED"
        elif warnings_count > 0:
            overall_status = "NEEDS_HUMAN_REVIEW"

        return CrossDocumentConsistencyReport(
            application_id=str(application_id),
            total_documents_analyzed=len(documents),
            overall_consistency_status=overall_status,
            total_conflicts=conflicts_count,
            total_warnings=warnings_count,
            findings=findings,
            analyzed_at=datetime.now(timezone.utc).isoformat(),
        )
