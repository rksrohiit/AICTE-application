"""
OCR and document intelligence service with page-level provenance.

Uses PyMuPDF (fitz) for native digital text extraction and PDF rendering,
PaddleOCR for scanned pages/images, TF-IDF cosine similarity for document
classification, and strict Pydantic schemas for extracted claims.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    TfidfVectorizer = None
    cosine_similarity = None

from app.schemas.extracted_claims import DocumentExtractionResult, ExtractedClaim

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

# ── Patterns for Field Extraction ────────────────────────────────────────────
_INDIAN_MONTHS = (
    "january|february|march|april|may|june|july|august|september|"
    "october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec"
)
_DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b"),
    re.compile(rf"\b(\d{{1,2}})\s+({_INDIAN_MONTHS})\s+(\d{{4}})\b", re.IGNORECASE),
]

_REF_PATTERN = re.compile(
    r"\b(AICTE[-/]\w+[-/]\d{4}(?:[-/]\d+)?|[A-Z]+-\d{4,}-\d+|F\.No\.[^\n,;]{5,40})\b",
    re.IGNORECASE,
)
_GRADE_PATTERN = re.compile(r"\b(A\+\+|A\+|A|B\+\+|B\+|B|C)\b")
_VALIDITY_PATTERN = re.compile(
    r"valid(?:ity|)\s*(?:from|till|up to|upto|period)?[:\s]*([^\n,;.]{5,60})",
    re.IGNORECASE,
)
_INST_NAME_PATTERNS = [
    re.compile(r"(?:name of institution|institution name|name of the institution)[:\s]+([^\n]{3,120})", re.IGNORECASE),
    re.compile(r"(?:institute|college|university)\s+of\s+[^\n]{3,80}", re.IGNORECASE),
    re.compile(r"(?:Dr\.|Shri|Sri)\s+[^\n]{3,80}(?:Institute|College|University)", re.IGNORECASE),
]
_INST_ID_PATTERNS = [
    re.compile(r"(?:AICTE\s*Permanent\s*ID|Permanent\s*Institute\s*ID|Institute\s*ID|Institution\s*Code)[:\s]+([A-Z0-9-]{4,20})", re.IGNORECASE),
    re.compile(r"\b(1-\d{8,12})\b"),
]
_ADDRESS_PATTERNS = [
    re.compile(r"(?:campus\s*address|institution\s*address|location|address)[:\s]+([^\n]{10,200})", re.IGNORECASE),
    re.compile(r"(?:situated\s*at|located\s*at|at\s*post)[:\s]+([^\n]{10,200})", re.IGNORECASE),
]
_ACADEMIC_YEAR_PATTERNS = [
    re.compile(r"\b(202\d[-/](?:20)?2\d)\b"),
    re.compile(r"(?:academic\s*year|session)[:\s]+(202\d[-/](?:20)?2\d)", re.IGNORECASE),
]
_PROGRAMME_PATTERNS = [
    re.compile(r"\b(ENGINEERING(?:\s+AND\s+TECHNOLOGY)?|MANAGEMENT|PHARMACY|ARCHITECTURE|MCA|MBA|COMPUTER\s+SCIENCE)\b", re.IGNORECASE),
]
_INTAKE_PATTERNS = [
    re.compile(r"(?:approved\s*intake|intake\s*capacity|intake)[:\s]+(\d{2,4})", re.IGNORECASE),
]
_SIGNATORY_PATTERN = re.compile(
    r"\b(signature|signed by|authorised signatory|authorized signatory|seal|stamp|director|principal)\b",
    re.IGNORECASE,
)


class OCRService:
    """Provides OCR text extraction, document classification, and structured claim extraction with page provenance."""

    def __init__(self) -> None:
        if PaddleOCR is not None:
            try:
                self._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
            except Exception:
                self._ocr = None
        else:
            self._ocr = None

        self._doc_types: List[str] = list(_DOC_KEYWORDS.keys())
        if TfidfVectorizer is not None:
            try:
                corpus = [" ".join(kws) for kws in _DOC_KEYWORDS.values()]
                self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
                self._doc_matrix = self._vectorizer.fit_transform(corpus)
            except Exception:
                self._vectorizer = None
                self._doc_matrix = None
        else:
            self._vectorizer = None
            self._doc_matrix = None

    # ── PDF / image I/O with page-level granularity ───────────────────────────

    def pdf_to_images(self, file_path: str) -> List[np.ndarray]:
        """Render each page of a PDF as an OpenCV-compatible NumPy image."""
        doc = fitz.open(file_path)
        images: List[np.ndarray] = []
        for page in doc:
            mat = fitz.Matrix(2.0, 2.0)  # ~150 DPI
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, 3
            )
            images.append(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        doc.close()
        return images

    def extract_text_by_pages(self, file_path: str) -> Tuple[Dict[int, str], int]:
        """Extract text page-by-page (1-indexed) preserving exact page numbers.

        Uses PyMuPDF direct text stream where available; falls back to PaddleOCR
        for scanned image pages.
        Returns: (pages_text_dict, total_pages)
        """
        path = Path(file_path)
        suffix = path.suffix.lower()
        pages_text: Dict[int, str] = {}

        if suffix == ".pdf":
            doc = fitz.open(file_path)
            total_pages = len(doc)
            for page_idx, page in enumerate(doc, start=1):
                text = page.get_text().strip()
                if len(text) >= 25:
                    pages_text[page_idx] = text
                else:
                    # Low digital text density: render page image and run OCR
                    mat = fitz.Matrix(1.5, 1.5)
                    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
                    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                        pix.height, pix.width, 3
                    )
                    bgr_img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                    ocr_res = self._ocr.ocr(bgr_img, cls=True)
                    ocr_lines = self._ocr_result_to_lines(ocr_res)
                    pages_text[page_idx] = "\n".join(ocr_lines)
            doc.close()
        else:
            total_pages = 1
            img = cv2.imread(file_path)
            if img is None:
                raise ValueError(f"Cannot read image file: {file_path}")
            ocr_res = self._ocr.ocr(img, cls=True)
            pages_text[1] = "\n".join(self._ocr_result_to_lines(ocr_res))

        return pages_text, max(total_pages, 1)

    def extract_text(self, file_path: str) -> str:
        """Extract all concatenated text from all pages (backwards compatibility)."""
        pages_text, _ = self.extract_text_by_pages(file_path)
        return "\n".join(pages_text.values())

    @staticmethod
    def _ocr_result_to_lines(result: Any) -> List[str]:
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
        if not text.strip():
            return "UNKNOWN", 0.0

        if (
            self._vectorizer is not None
            and self._doc_matrix is not None
            and cosine_similarity is not None
            and np is not None
        ):
            try:
                query_vec = self._vectorizer.transform([text.lower()])
                sims = cosine_similarity(query_vec, self._doc_matrix).flatten()
                best_idx = int(np.argmax(sims))
                confidence = float(sims[best_idx])
                if confidence >= 0.05:
                    return self._doc_types[best_idx], round(confidence, 4)
            except Exception:
                pass

        # Heuristic keyword fallback
        text_lower = text.lower()
        best_doc = "UNKNOWN"
        best_count = 0
        for doc_type, keywords in _DOC_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw.lower() in text_lower)
            if count > best_count:
                best_count = count
                best_doc = doc_type

        conf = min(0.95, round(best_count / 4.0, 2)) if best_count > 0 else 0.0
        return best_doc, conf

    # ── Structured Claims Extraction with Strict Provenance ────────────────────

    def extract_structured_claims(
        self,
        pages_dict: Dict[int, str],
        doc_type: str,
        total_pages: int,
    ) -> List[ExtractedClaim]:
        """Extract verifiable claims across pages with honest missing field policy."""
        claims: List[ExtractedClaim] = []

        # Helper to search for a pattern across pages and record first reliable match
        def _find_claim(
            field_name: str,
            patterns: List[re.Pattern],
            base_confidence: float = 0.88,
        ) -> Optional[ExtractedClaim]:
            for page_num in range(1, total_pages + 1):
                page_text = pages_dict.get(page_num, "")
                for pat in patterns:
                    m = pat.search(page_text)
                    if m:
                        val = m.group(1).strip() if m.groups() else m.group(0).strip()
                        # Clean surrounding snippet (up to 120 chars)
                        start = max(0, m.start() - 20)
                        end = min(len(page_text), m.end() + 40)
                        snippet = page_text[start:end].replace("\n", " ").strip()
                        return ExtractedClaim(
                            field_name=field_name,
                            value=val,
                            page_number=page_num,
                            confidence=base_confidence,
                            source_type="pdf_text" if len(page_text) > 100 else "ocr",
                            raw_snippet=snippet,
                            status="VERIFIED",
                        )
            return None

        # 1. Institution Name
        inst_claim = _find_claim("institution_name", _INST_NAME_PATTERNS, 0.92)
        if inst_claim:
            claims.append(inst_claim)
        else:
            claims.append(
                ExtractedClaim(
                    field_name="institution_name",
                    value=None,
                    page_number=1,
                    confidence=0.0,
                    status="NOT_FOUND",
                )
            )

        # 2. Institution / AICTE ID
        id_claim = _find_claim("institution_id", _INST_ID_PATTERNS, 0.95)
        if id_claim:
            claims.append(id_claim)

        # 3. Address
        addr_claim = _find_claim("address", _ADDRESS_PATTERNS, 0.88)
        if addr_claim:
            claims.append(addr_claim)

        # 4. Academic Year
        ay_claim = _find_claim("academic_year", _ACADEMIC_YEAR_PATTERNS, 0.94)
        if ay_claim:
            claims.append(ay_claim)

        # 5. Approval / Reference Number
        ref_claim = _find_claim("approval_ref_number", [_REF_PATTERN], 0.92)
        if ref_claim:
            claims.append(ref_claim)

        # 6. Approved Programme
        prog_claim = _find_claim("approved_programme", _PROGRAMME_PATTERNS, 0.90)
        if prog_claim:
            claims.append(prog_claim)

        # 7. Approved Intake Capacity
        intake_claim = _find_claim("intake_capacity", _INTAKE_PATTERNS, 0.89)
        if intake_claim:
            claims.append(intake_claim)

        # 8. NAAC Grade (for NAAC_CERT)
        if doc_type == "NAAC_CERT":
            naac_claim = _find_claim("naac_grade", [_GRADE_PATTERN], 0.95)
            if naac_claim:
                claims.append(naac_claim)

        # 9. Signatory & Official Seal
        sig_claim = _find_claim("signatory_present", [_SIGNATORY_PATTERN], 0.85)
        if sig_claim:
            sig_claim.value = True
            claims.append(sig_claim)
        else:
            claims.append(
                ExtractedClaim(
                    field_name="signatory_present",
                    value=False,
                    page_number=total_pages,
                    confidence=0.5,
                    status="UNCERTAIN",
                )
            )

        # 10. Dates
        all_dates: List[Tuple[str, int]] = []
        for p_num, p_text in pages_dict.items():
            for pat in _DATE_PATTERNS:
                for match in pat.finditer(p_text):
                    all_dates.append((match.group(0).strip(), p_num))
        if all_dates:
            first_date, d_page = all_dates[0]
            claims.append(
                ExtractedClaim(
                    field_name="document_date",
                    value=first_date,
                    page_number=d_page,
                    confidence=0.92,
                    raw_snippet=f"Detected date {first_date} on page {d_page}",
                    status="VERIFIED",
                )
            )

        return claims

    # ── Backwards compatible extract_fields method ────────────────────────────

    def extract_fields(self, text: str, doc_type: str) -> Dict[str, Dict[str, Any]]:
        """Legacy dictionary representation for existing tests."""
        pages = {1: text}
        claims = self.extract_structured_claims(pages, doc_type, 1)
        fields: Dict[str, Dict[str, Any]] = {}
        for c in claims:
            fields[c.field_name] = {
                "value": c.value,
                "confidence": c.confidence,
                "page": c.page_number,
                "status": c.status,
            }
        return fields

    @staticmethod
    def compute_file_hash(file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
