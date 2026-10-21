"""
OCR and document intelligence service.

Uses PaddleOCR for text extraction, PyMuPDF for PDF-to-image rendering,
and scikit-learn TF-IDF cosine similarity for document classification.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import fitz  # PyMuPDF
import numpy as np
from paddleocr import PaddleOCR
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ── Document type keyword corpora ────────────────────────────────────────────
_DOC_KEYWORDS: Dict[str, List[str]] = {
    "AFFIDAVIT": [
        "affidavit", "solemnly affirm", "sworn", "deponent", "notary",
        "advocate", "commissioner of oaths", "stamp duty", "judicial",
        "declaration", "undertaking", "duly sworn", "depose",
    ],
    "STATE_NOC": [
        "no objection certificate", "NOC", "state government", "directorate",
        "technical education", "state board", "approval", "permission granted",
        "eligible", "state level", "director", "state noc",
    ],
    "NAAC_CERT": [
        "NAAC", "national assessment", "accreditation council", "grade",
        "A++", "A+", "CGPA", "accredited", "peer team", "cycle", "validity",
        "assessment report", "quality", "reaccreditation",
    ],
    "FIRE_SAFETY_CERT": [
        "fire safety", "fire NOC", "fire department", "fire officer",
        "fire brigade", "fire extinguisher", "evacuation", "sprinkler",
        "fire fighting", "safety certificate", "fire station",
    ],
    "TER_RECEIPT": [
        "tuition fee receipt", "TER", "fee regulatory", "payment receipt",
        "challan", "treasury", "bank receipt", "transaction ID",
        "tuition fee", "regulatory fee", "payment confirmation",
    ],
    "LAND_BUILDING_DOC": [
        "land document", "building plan", "property", "survey number",
        "ownership", "lease deed", "sale deed", "area", "sq ft", "sq m",
        "building approval", "municipal", "construction", "land record",
    ],
    "FACULTY_DATA": [
        "faculty", "staff", "teaching", "qualification", "designation",
        "professor", "assistant professor", "associate professor", "lecturer",
        "Ph.D", "M.Tech", "B.Tech", "experience", "department", "UGC",
    ],
    "EOA_FORM": [
        "extension of approval", "EOA", "AICTE", "application form",
        "academic year", "programme", "intake", "institution code",
        "continuation", "renewal", "form A", "form B", "approval number",
    ],
}

# ── Indian date pattern ───────────────────────────────────────────────────────
_INDIAN_MONTHS = (
    "january|february|march|april|may|june|july|august|september|"
    "october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec"
)
_DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b"),
    re.compile(
        rf"\b(\d{{1,2}})\s+({_INDIAN_MONTHS})\s+(\d{{4}})\b", re.IGNORECASE
    ),
]

# ── AICTE reference number pattern ───────────────────────────────────────────
_REF_PATTERN = re.compile(
    r"\b(AICTE[-/]\w+[-/]\d{4}(?:[-/]\d+)?|[A-Z]+-\d{4,}-\d+)\b", re.IGNORECASE
)

# ── NAAC grade pattern ────────────────────────────────────────────────────────
_GRADE_PATTERN = re.compile(r"\b(A\+\+|A\+|A|B\+\+|B\+|B|C)\b")

# ── Validity period pattern ───────────────────────────────────────────────────
_VALIDITY_PATTERN = re.compile(
    r"valid(?:ity|)\s*(?:from|till|up to|upto|period)?[:\s]*([^\n,;.]{5,60})",
    re.IGNORECASE,
)

# ── Institution name patterns ─────────────────────────────────────────────────
_INST_NAME_PATTERNS = [
    re.compile(r"(?:name of institution|institution name|name of the institution)[:\s]+([^\n]{3,120})", re.IGNORECASE),
    re.compile(r"(?:institution|college|university|institute)[:\s]+([^\n]{3,120})", re.IGNORECASE),
]

# ── Signatory keywords ────────────────────────────────────────────────────────
_SIGNATORY_PATTERN = re.compile(
    r"\b(signature|signed by|authorised signatory|authorized signatory|seal|stamp)\b",
    re.IGNORECASE,
)


class OCRService:
    """Provides OCR text extraction, document classification, and field extraction."""

    def __init__(self) -> None:
        """Initialise PaddleOCR with angle classification enabled for Indian documents."""
        self._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

        # ── Precompute TF-IDF matrix for classification ───────────────────────
        self._doc_types: List[str] = list(_DOC_KEYWORDS.keys())
        corpus = [" ".join(kws) for kws in _DOC_KEYWORDS.values()]
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        self._doc_matrix = self._vectorizer.fit_transform(corpus)

    # ── PDF / image I/O ───────────────────────────────────────────────────────

    def pdf_to_images(self, file_path: str) -> List[np.ndarray]:
        """Render each page of a PDF as an OpenCV-compatible NumPy image.

        Args:
            file_path: Absolute path to the PDF file.

        Returns:
            List of ``uint8`` BGR NumPy arrays, one per page.
        """
        doc = fitz.open(file_path)
        images: List[np.ndarray] = []
        for page in doc:
            mat = fitz.Matrix(2.0, 2.0)  # 2× zoom → ~150 DPI
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, 3
            )
            images.append(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        doc.close()
        return images

    def extract_text(self, file_path: str) -> str:
        """Extract all text from a PDF or image file using PaddleOCR.

        For PDFs, each page is rendered to an image first.
        For image files (JPEG, PNG, TIFF), the image is read directly.

        Args:
            file_path: Absolute path to the document file.

        Returns:
            Concatenated OCR text from all pages / the single image.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()
        text_lines: List[str] = []

        if suffix == ".pdf":
            images = self.pdf_to_images(file_path)
            for img in images:
                result = self._ocr.ocr(img, cls=True)
                text_lines.extend(self._ocr_result_to_lines(result))
        else:
            img = cv2.imread(file_path)
            if img is None:
                raise ValueError(f"Cannot read image file: {file_path}")
            result = self._ocr.ocr(img, cls=True)
            text_lines.extend(self._ocr_result_to_lines(result))

        return "\n".join(text_lines)

    @staticmethod
    def _ocr_result_to_lines(result: Any) -> List[str]:
        """Flatten a PaddleOCR result list into text lines.

        Args:
            result: Raw PaddleOCR output (list of pages/blocks).

        Returns:
            Flat list of non-empty text strings.
        """
        lines: List[str] = []
        if result is None:
            return lines
        for page in result:
            if page is None:
                continue
            for block in page:
                if block and len(block) >= 2:
                    text_info = block[1]
                    if isinstance(text_info, (list, tuple)) and len(text_info) >= 1:
                        text = text_info[0]
                        if isinstance(text, str) and text.strip():
                            lines.append(text.strip())
        return lines

    # ── Classification ────────────────────────────────────────────────────────

    def classify_document(self, text: str) -> Tuple[str, float]:
        """Classify the document type using TF-IDF cosine similarity.

        Args:
            text: Extracted OCR text from the document.

        Returns:
            A ``(doc_type, confidence)`` tuple where *confidence* is in [0, 1].
        """
        if not text.strip():
            return "UNKNOWN", 0.0

        query_vec = self._vectorizer.transform([text.lower()])
        sims = cosine_similarity(query_vec, self._doc_matrix).flatten()
        best_idx = int(np.argmax(sims))
        confidence = float(sims[best_idx])

        if confidence < 0.05:
            return "UNKNOWN", confidence

        return self._doc_types[best_idx], round(confidence, 4)

    # ── Field extraction ──────────────────────────────────────────────────────

    def extract_fields(self, text: str, doc_type: str) -> Dict[str, Dict[str, Any]]:
        """Extract structured fields from OCR text based on the document type.

        Extracted fields (when present):
        - ``dates``: all detected date strings
        - ``institution_name``: extracted institution name
        - ``reference_numbers``: AICTE / government reference numbers
        - ``naac_grade``: NAAC accreditation grade (NAAC_CERT only)
        - ``validity_period``: validity statement
        - ``signatory_present``: boolean — signature/seal keyword found

        Args:
            text:     OCR-extracted text from the document.
            doc_type: Classified or declared document type string.

        Returns:
            Dict mapping field names to ``{"value": ..., "confidence": float}``.
        """
        fields: Dict[str, Dict[str, Any]] = {}

        # ── Dates ─────────────────────────────────────────────────────────────
        dates: List[str] = []
        for pat in _DATE_PATTERNS:
            for match in pat.finditer(text):
                dates.append(match.group(0).strip())
        fields["dates"] = {"value": list(dict.fromkeys(dates)), "confidence": 0.9 if dates else 0.0}

        # ── Institution name ──────────────────────────────────────────────────
        inst_name: str | None = None
        for pat in _INST_NAME_PATTERNS:
            m = pat.search(text)
            if m:
                inst_name = m.group(1).strip()
                break
        fields["institution_name"] = {
            "value": inst_name,
            "confidence": 0.85 if inst_name else 0.0,
        }

        # ── Reference / approval numbers ──────────────────────────────────────
        ref_numbers = [m.group(0) for m in _REF_PATTERN.finditer(text)]
        fields["reference_numbers"] = {
            "value": list(dict.fromkeys(ref_numbers)),
            "confidence": 0.95 if ref_numbers else 0.0,
        }

        # ── NAAC grade (relevant for NAAC_CERT) ───────────────────────────────
        if doc_type == "NAAC_CERT":
            grade_match = _GRADE_PATTERN.search(text)
            fields["naac_grade"] = {
                "value": grade_match.group(1) if grade_match else None,
                "confidence": 0.9 if grade_match else 0.0,
            }
        else:
            fields["naac_grade"] = {"value": None, "confidence": 0.0}

        # ── Validity period ───────────────────────────────────────────────────
        validity_match = _VALIDITY_PATTERN.search(text)
        fields["validity_period"] = {
            "value": validity_match.group(1).strip() if validity_match else None,
            "confidence": 0.8 if validity_match else 0.0,
        }

        # ── Signatory present ─────────────────────────────────────────────────
        signatory_found = bool(_SIGNATORY_PATTERN.search(text))
        fields["signatory_present"] = {
            "value": signatory_found,
            "confidence": 0.75 if signatory_found else 0.5,
        }

        return fields

    # ── File integrity ────────────────────────────────────────────────────────

    @staticmethod
    def compute_file_hash(file_path: str) -> str:
        """Compute the SHA-256 hex digest of a file.

        Args:
            file_path: Absolute path to the file.

        Returns:
            64-character lowercase hex string.
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
