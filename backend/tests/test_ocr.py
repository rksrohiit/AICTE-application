"""
test_ocr.py — Tests for OCR extraction, classification, and parsing utilities.
Compatible with standard unittest and pytest.
"""

import tempfile
import unittest
from pathlib import Path

from app.services.ocr.extractor import OCRService


class TestOCRService(unittest.TestCase):
    """Verify document classification, field extraction, and hashing."""

    def test_document_classification_affidavit(self):
        """Verify affidavit text is classified accurately with high confidence."""
        text = (
            "BEFORE THE NOTARY PUBLIC, GOVT OF MAHARASHTRA. "
            "AFFIDAVIT of Dr. R. K. Sharma. I solemnly affirm and deponent states that "
            "the information provided is true and correct under oath. Duly sworn on stamp duty."
        )
        svc = OCRService()
        doc_type, conf = svc.classify_document(text)
        self.assertEqual(doc_type, "AFFIDAVIT")
        self.assertGreater(conf, 0.1)

    def test_document_classification_noc(self):
        """Verify State NOC text is classified accurately."""
        text = (
            "GOVERNMENT OF MAHARASHTRA DIRECTORATE OF TECHNICAL EDUCATION. "
            "NO OBJECTION CERTIFICATE (NOC). Approval and permission granted for extension of approval."
        )
        svc = OCRService()
        doc_type, conf = svc.classify_document(text)
        self.assertEqual(doc_type, "STATE_NOC")
        self.assertGreater(conf, 0.1)

    def test_extract_date_fields(self):
        """Verify date pattern extraction on Indian date representations."""
        text = "Issued on 15/08/2024 and valid until 31-12-2025. Meeting held on 10 October 2024."
        svc = OCRService()
        fields = svc.extract_fields(text, "AFFIDAVIT")
        self.assertIn("document_date", fields)
        date_val = fields["document_date"]["value"]
        self.assertIn("2024", date_val)
        self.assertEqual(fields["document_date"]["status"], "VERIFIED")

    def test_extract_institution_name(self):
        """Verify extraction of institution name from key-value text."""
        text = "Name of Institution: Bharati Vidyapeeth College of Engineering, Pune."
        svc = OCRService()
        fields = svc.extract_fields(text, "EOA_FORM")
        self.assertIn("institution_name", fields)
        name = fields["institution_name"]["value"]
        self.assertIn("Bharati Vidyapeeth", name)

    def test_compute_file_hash(self):
        """Verify SHA-256 calculation on arbitrary file content."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"AICTE Demo Application Test Content")
            tmp_path = tmp.name

        try:
            svc = OCRService()
            file_hash = svc.compute_file_hash(tmp_path)
            self.assertEqual(len(file_hash), 64)
            self.assertTrue(file_hash.isalnum())
        finally:
            Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
