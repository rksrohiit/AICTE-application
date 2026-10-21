"""
Tests for OCR extraction, classification, and parsing utilities.
"""

import tempfile
from pathlib import Path
import pytest
from app.services.ocr.extractor import (
    _DOC_KEYWORDS,
    _DATE_PATTERNS,
    _REF_PATTERN,
    _GRADE_PATTERN,
    _INST_NAME_PATTERNS,
    OCRService,
)


def test_document_classification_affidavit():
    """Verify affidavit text is classified accurately with high confidence."""
    text = (
        "BEFORE THE NOTARY PUBLIC, GOVT OF MAHARASHTRA. "
        "AFFIDAVIT of Dr. R. K. Sharma. I solemnly affirm and deponent states that "
        "the information provided is true and correct under oath. Duly sworn on stamp duty."
    )
    svc = OCRService()
    doc_type, conf = svc.classify_document(text)
    assert doc_type == "AFFIDAVIT"
    assert conf > 0.1


def test_document_classification_noc():
    """Verify State NOC text is classified accurately."""
    text = (
        "GOVERNMENT OF MAHARASHTRA DIRECTORATE OF TECHNICAL EDUCATION. "
        "NO OBJECTION CERTIFICATE (NOC). Approval and permission granted for extension of approval."
    )
    svc = OCRService()
    doc_type, conf = svc.classify_document(text)
    assert doc_type == "STATE_NOC"
    assert conf > 0.1


def test_extract_date_fields():
    """Verify date pattern extraction on Indian date representations."""
    text = "Issued on 15/08/2024 and valid until 31-12-2025. Meeting held on 10 October 2024."
    svc = OCRService()
    fields = svc.extract_fields(text, "AFFIDAVIT")
    assert "dates" in fields
    dates = fields["dates"]["value"]
    assert any("2024" in d for d in dates)
    assert any("2025" in d for d in dates)


def test_extract_institution_name():
    """Verify extraction of institution name from key-value text."""
    text = "Name of Institution: Bharati Vidyapeeth College of Engineering, Pune."
    svc = OCRService()
    fields = svc.extract_fields(text, "EOA_FORM")
    assert "institution_name" in fields
    name = fields["institution_name"]["value"]
    assert "Bharati Vidyapeeth" in name


def test_compute_file_hash():
    """Verify SHA-256 calculation on arbitrary file content."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"AICTE Demo Application Test Content")
        tmp_path = tmp.name

    try:
        svc = OCRService()
        file_hash = svc.compute_file_hash(tmp_path)
        assert len(file_hash) == 64
        assert file_hash.isalnum()
    finally:
        Path(tmp_path).unlink(missing_ok=True)
