"""
OCR Celery tasks: process a document through the OCR pipeline and persist results.
"""

from __future__ import annotations

import os
import tempfile
import traceback
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.tasks.celery_app import celery_app

# ── Sync engine for Celery (asyncpg is async-only; use psycopg2 here) ─────────
_sync_engine = create_engine(
    settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    .replace("postgresql://", "postgresql+psycopg2://")
    if "asyncpg" in settings.DATABASE_URL
    else settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://"),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
SyncSession = sessionmaker(bind=_sync_engine, autoflush=False, autocommit=False)


def _get_sync_session() -> Session:
    """Return a new synchronous SQLAlchemy session for Celery worker use."""
    return SyncSession()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="app.tasks.ocr_tasks.process_document_ocr",
)
def process_document_ocr(self, document_id: str) -> dict:
    """OCR processing pipeline for a single uploaded document.

    Steps:
    1. Load the :class:`~app.models.document.Document` record from the database.
    2. Download the file from MinIO to a temporary directory.
    3. Run :meth:`~app.services.ocr.extractor.OCRService.extract_text`.
    4. Run :meth:`~app.services.ocr.extractor.OCRService.classify_document`.
    5. Run :meth:`~app.services.ocr.extractor.OCRService.extract_fields`.
    6. Compute the SHA-256 file hash.
    7. Persist ``extracted_data``, ``file_hash``, and ``ocr_status=COMPLETE`` to the DB.
    8. Write an :class:`~app.models.audit.AuditLog` entry.

    Args:
        document_id: UUID string of the :class:`~app.models.document.Document`.

    Returns:
        Dict summarising the outcome.
    """
    from app.models.document import Document, OCRStatus
    from app.models.audit import AuditLog
    from app.services.ocr.extractor import OCRService
    from app.services.ocr.storage import StorageService

    db: Session = _get_sync_session()
    tmp_path: str | None = None

    try:
        doc_uuid = uuid.UUID(document_id)
        doc: Document | None = db.get(Document, doc_uuid)

        if doc is None:
            return {"error": f"Document {document_id} not found."}

        # ── Mark as processing (Idempotent start) ────────────────────────────
        doc.ocr_status = OCRStatus.PROCESSING
        doc.processing_status = "PROCESSING"
        doc.error_message = None
        doc.updated_at = datetime.now(timezone.utc)
        db.commit()

        # ── Download from MinIO ───────────────────────────────────────────────
        storage = StorageService()
        suffix = os.path.splitext(doc.file_name)[1] or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name

        storage.download_file(doc.file_path, tmp_path)

        # ── OCR & Structured Extraction with Provenance ───────────────────────
        ocr = OCRService()
        pages_dict, total_pages = ocr.extract_text_by_pages(tmp_path)
        all_text = "\n".join(pages_dict.values())
        doc_type_detected, classification_confidence = ocr.classify_document(all_text)
        
        # Extract structured verifiable claims with page provenance
        structured_claims = ocr.extract_structured_claims(
            pages_dict=pages_dict,
            doc_type=doc_type_detected,
            total_pages=total_pages,
        )
        file_hash = ocr.compute_file_hash(tmp_path)

        # Validate extraction result schema & page bounds
        from app.schemas.extracted_claims import DocumentExtractionResult
        extraction_res = DocumentExtractionResult(
            document_id=str(doc.id),
            doc_type=doc_type_detected,
            total_pages=total_pages,
            file_hash=file_hash,
            claims=structured_claims,
            extraction_status="SUCCESS",
            processed_at=datetime.now(timezone.utc).isoformat(),
        )
        page_validation_errors = extraction_res.validate_page_references()

        # ── Persist idempotent results ────────────────────────────────────────
        doc.extracted_data = {
            "raw_text_length": len(all_text),
            "total_pages": total_pages,
            "detected_doc_type": doc_type_detected,
            "classification_confidence": classification_confidence,
            "page_validation_errors": page_validation_errors,
            "fields": ocr.extract_fields(all_text, doc_type_detected),
        }
        doc.extracted_claims = [c.model_dump() for c in structured_claims]
        doc.file_hash = file_hash
        doc.ocr_status = OCRStatus.COMPLETE
        doc.processing_status = "EXTRACTED"
        doc.error_message = None
        doc.updated_at = datetime.now(timezone.utc)

        audit = AuditLog(
            actor="SYSTEM",
            action="DOCUMENT_EXTRACTED",
            application_id=doc.application_id,
            document_id=doc.id,
            result="SUCCESS",
            notes=(
                f"Extracted {len(structured_claims)} claims across {total_pages} pages. "
                f"Type: {doc_type_detected} (conf: {classification_confidence:.2f})"
            ),
        )
        db.add(audit)
        db.commit()

        return {
            "document_id": document_id,
            "status": "EXTRACTED",
            "total_pages": total_pages,
            "claims_count": len(structured_claims),
            "detected_doc_type": doc_type_detected,
            "file_hash": file_hash,
        }

    except Exception as exc:
        db.rollback()
        # Non-fatal handling: record FAILED status on document without failing application
        try:
            doc_uuid = uuid.UUID(document_id)
            doc = db.get(Document, doc_uuid)
            if doc:
                from app.models.document import OCRStatus as _OCRStatus
                doc.ocr_status = _OCRStatus.FAILED
                doc.processing_status = "FAILED"
                doc.error_message = f"Processing exception: {str(exc)}"
                doc.updated_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            db.rollback()

        raise self.retry(exc=exc)
    finally:
        db.close()
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
