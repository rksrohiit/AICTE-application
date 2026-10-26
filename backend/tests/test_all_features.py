"""
test_all_features.py - End-to-end unit test suite for AICTE validation features.
Uses Python standard unittest library for universal portability.
"""

import unittest
import hashlib
from datetime import datetime, timezone

from app.services.cross_document import (
    normalize_field_value,
    compute_token_similarity,
    AUTHORITATIVE_DOCS,
)
from app.services.audit_chain import (
    compute_audit_hash,
    GENESIS_HASH,
    generate_qr_code_data_uri,
)
from app.services.campus_geo import (
    CampusGeoService,
    AICTE_MIN_LAND_NORMS,
)
from app.services.ocr.extractor import OCRService
from app.api.v1.routes.documents import validate_magic_bytes


class TestCrossDocumentConsistency(unittest.TestCase):
    """Test Cross-Document Consistency Engine field normalizations and similarity algorithms."""

    def test_abbreviation_normalization(self):
        # Institution name normalization
        name_a = "Bharati Vidyapeeth Inst. of Tech. & Engg."
        name_b = "Bharati Vidyapeeth Institute of Technology and Engineering"
        norm_a = normalize_field_value(name_a, "institution_name")
        norm_b = normalize_field_value(name_b, "institution_name")
        self.assertEqual(norm_a, norm_b)

        # Academic year normalization
        year_a = "2024-25"
        year_b = "2024-2025"
        self.assertEqual(
            normalize_field_value(year_a, "academic_year"),
            normalize_field_value(year_b, "academic_year"),
        )

    def test_text_similarity_identical_and_divergent(self):
        # Near identical with minor abbreviation
        score_high = compute_token_similarity(
            "Govt College of Engineering Pune",
            "Government College of Engineering Pune",
        )
        self.assertGreaterEqual(score_high, 0.70)

        # Completely divergent names
        score_low = compute_token_similarity(
            "Delhi Technological University",
            "Indian Institute of Science Bangalore",
        )
        self.assertLess(score_low, 0.40)

    def test_authoritative_mapping_coverage(self):
        self.assertIn("institution_name", AUTHORITATIVE_DOCS)
        self.assertIn("institution_id", AUTHORITATIVE_DOCS)
        self.assertIn("address", AUTHORITATIVE_DOCS)
        self.assertIn("EOA_FORM", AUTHORITATIVE_DOCS["institution_name"])
        self.assertIn("LAND_BUILDING_DOC", AUTHORITATIVE_DOCS["address"])


class TestCryptographicAuditChain(unittest.TestCase):
    """Test SHA-256 Hash Chained Audit Trail and Tamper Resistance."""

    def test_hash_chain_computation(self):
        prev = GENESIS_HASH
        t1 = "2026-10-24T10:00:00Z"
        h1 = compute_audit_hash(prev, t1, "OFFICER_001", "APPROVE_FOR_PROCESSING", "APP_123")
        self.assertEqual(len(h1), 64)
        self.assertTrue(h1.isalnum())

        # Link second record
        t2 = "2026-10-24T10:05:00Z"
        h2 = compute_audit_hash(h1, t2, "SYSTEM", "GENERATE_EOA", "APP_123")
        self.assertEqual(len(h2), 64)
        self.assertNotEqual(h1, h2)

    def test_tamper_detection(self):
        # If record 1 is retroactively edited, h2 calculated from edited h1 will differ
        prev = GENESIS_HASH
        t1 = "2026-10-24T10:00:00Z"
        original_h1 = compute_audit_hash(prev, t1, "OFFICER_001", "APPROVE_FOR_PROCESSING", "APP_123")
        tampered_h1 = compute_audit_hash(prev, t1, "OFFICER_001", "REJECT", "APP_123")
        self.assertNotEqual(original_h1, tampered_h1)

    def test_qr_generation(self):
        qr_uri = generate_qr_code_data_uri("https://aicte.gov.in/verify/APP_123")
        self.assertTrue(qr_uri.startswith("data:image/png;base64,"))


class TestCampusGeoVerification(unittest.TestCase):
    """Test geodesic plot boundary polygon area and APH norms."""

    def test_geodesic_polygon_area(self):
        # A quadrilateral campus (~ 100m x 100m = ~ 10,000 sqm = ~ 1 hectare = ~ 2.47 acres)
        coords = [
            [18.5204, 73.8567],
            [18.5213, 73.8567],
            [18.5213, 73.8576],
            [18.5204, 73.8576],
        ]
        result = CampusGeoService.calculate_polygon_geodesic(coords)
        self.assertIn("area_sq_meters", result)
        self.assertIn("area_acres", result)
        self.assertIn("perimeter_meters", result)
        self.assertGreater(result["area_sq_meters"], 5000)
        self.assertGreater(result["area_acres"], 1.0)

    def test_invalid_polygon_raises(self):
        with self.assertRaises(ValueError):
            CampusGeoService.calculate_polygon_geodesic([[18.5, 73.8], [18.6, 73.9]])


class TestMagicBytesValidation(unittest.TestCase):
    """Test binary magic-byte content validation against spoofed headers."""

    def test_valid_pdf_magic_bytes(self):
        content = b"%PDF-1.7\r\nsome valid binary stream..."
        self.assertTrue(validate_magic_bytes(content))

    def test_valid_jpeg_magic_bytes(self):
        content = b"\xff\xd8\xff\xe0\x00\x10JFIF..."
        self.assertTrue(validate_magic_bytes(content))

    def test_valid_png_magic_bytes(self):
        content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR..."
        self.assertTrue(validate_magic_bytes(content))

    def test_spoofed_file_blocked(self):
        # Text file masquerading as a PDF
        spoofed = b"This is just a plaintext file named evil.pdf"
        self.assertFalse(validate_magic_bytes(spoofed))


class TestOCRClassification(unittest.TestCase):
    """Test OCR service document classification and keyword heuristics."""

    def test_affidavit_classification(self):
        svc = OCRService()
        text = "AFFIDAVIT. In the presence of Notary Public, I hereby affirm on solemn oath and stamp duty..."
        doc_type, conf = svc.classify_document(text)
        self.assertEqual(doc_type, "AFFIDAVIT")
        self.assertGreater(conf, 0.1)

    def test_state_noc_classification(self):
        svc = OCRService()
        text = "GOVERNMENT OF MAHARASHTRA DIRECTORATE OF TECHNICAL EDUCATION. NO OBJECTION CERTIFICATE (NOC)."
        doc_type, conf = svc.classify_document(text)
        self.assertEqual(doc_type, "STATE_NOC")
        self.assertGreater(conf, 0.1)


if __name__ == "__main__":
    unittest.main()
