"""
extracted_claims.py — Strict Pydantic V2 Schemas for Verifiable Document Claims
AICTE AI-Powered Application Validation Platform

Principles:
- Strict typing and validation: AI and OCR extractions must conform to this schema,
  never unstructured free-form text.
- Page-level provenance: Every extracted field must cite its exact page number.
- Honest missing field policy: If a field is not found or ambiguous, return
  explicit NOT_FOUND or UNCERTAIN status. Never synthesize plausible dummy values.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class ExtractedClaim(BaseModel):
    """A single structured claim extracted from a document with strict provenance."""

    field_name: str = Field(
        ...,
        description="Canonical field name, e.g., institution_name, address, academic_year",
    )
    value: Any = Field(
        None,
        description="Extracted value (string, number, or boolean), or null if not detected",
    )
    page_number: int = Field(
        ...,
        description="1-indexed physical page where the claim appears in the document",
        ge=1,
    )
    confidence: float = Field(
        ...,
        description="Model or heuristic confidence score [0.0 - 1.0]. Not calibrated as a true probability.",
        ge=0.0,
        le=1.0,
    )
    source_type: Literal["ocr", "pdf_text", "rule", "manual_entry"] = Field(
        "ocr", description="Extraction mechanism"
    )
    raw_snippet: Optional[str] = Field(
        None, description="Exact verbatim context sentence or phrase from the document page"
    )
    status: Literal["VERIFIED", "UNCERTAIN", "NOT_FOUND"] = Field(
        "VERIFIED",
        description="Extraction certainty. 'UNCERTAIN' if confidence is marginal; 'NOT_FOUND' if absent.",
    )

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 4)


class DocumentExtractionResult(BaseModel):
    """Complete structured extraction response for a processed document."""

    document_id: str
    doc_type: str
    total_pages: int = Field(..., ge=1)
    file_hash: str
    claims: List[ExtractedClaim] = Field(default_factory=list)
    extraction_status: Literal["SUCCESS", "PARTIAL", "FAILED"] = "SUCCESS"
    error_message: Optional[str] = None
    processed_at: str

    def validate_page_references(self) -> List[str]:
        """Verify that every cited page number exists within the document page count."""
        errors = []
        for claim in self.claims:
            if claim.page_number > self.total_pages:
                errors.append(
                    f"Claim '{claim.field_name}' cites page {claim.page_number}, but document has only {self.total_pages} pages."
                )
        return errors
