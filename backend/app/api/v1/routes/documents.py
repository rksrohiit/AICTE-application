"""
Document upload and retrieval routes.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.application import Application
from app.models.document import Document, DocumentType, OCRStatus
from app.models.user import User, UserRole
from app.schemas.document import DocumentResponse, DocumentUploadResponse

router = APIRouter(tags=["documents"])

_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
}
_MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


def validate_magic_bytes(file_bytes: bytes) -> bool:
    """Validate actual binary signature (magic bytes), not just user-declared extension."""
    return (
        file_bytes.startswith(b"%PDF-")  # Genuine PDF
        or file_bytes.startswith(b"\xff\xd8\xff")  # Genuine JPEG
        or file_bytes.startswith(b"\x89PNG\r\n\x1a\n")  # Genuine PNG
        or file_bytes.startswith(b"II*\x00")
        or file_bytes.startswith(b"MM\x00*")  # TIFF
    )


async def _get_application_or_404(
    app_id: uuid.UUID,
    db: AsyncSession,
    current_user: User,
) -> Application:
    """Fetch an application by UUID with role-based visibility.

    Args:
        app_id:       Application UUID.
        db:           Async database session.
        current_user: Authenticated user.

    Returns:
        The :class:`Application` ORM instance.

    Raises:
        :class:`~fastapi.HTTPException` 404: If not found or not accessible.
    """
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    if current_user.role == UserRole.INSTITUTION and app.institution_id != current_user.institution_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    return app


@router.post(
    "/applications/{app_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document for an application",
)
async def upload_document(
    app_id: uuid.UUID,
    doc_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentUploadResponse:
    """Upload a document file and enqueue OCR processing.

    Args:
        app_id:       Application UUID.
        doc_type:     Document category (form field).
        file:         Uploaded file (multipart/form-data).
        db:           Async database session.
        current_user: Authenticated user.

    Returns:
        A :class:`DocumentUploadResponse` with the new document ID.
    """
    from app.services.ocr.storage import StorageService
    from app.tasks.ocr_tasks import process_document_ocr

    app = await _get_application_or_404(app_id, db, current_user)

    # ── MIME type & true content magic bytes guard ────────────────────────────
    file_bytes = await file.read()
    file_size = len(file_bytes)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    if file_size > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {_MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    # Validate actual binary signature (magic bytes), not just user-declared extension
    if not validate_magic_bytes(file_bytes):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid file signature: Content is not a genuine PDF or image binary.",
        )

    # ── Save to a temp file and upload to MinIO ──────────────────────────────
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename or "doc")[1]) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        storage = StorageService()
        storage.ensure_bucket_exists()
        minio_path = storage.upload_file(
            local_path=tmp_path,
            application_id=str(app_id),
            doc_type=doc_type.value,
            filename=file.filename or f"{doc_type.value}.pdf",
        )
    finally:
        os.unlink(tmp_path)

    # ── Create Document record ───────────────────────────────────────────────
    doc = Document(
        application_id=app_id,
        doc_type=doc_type,
        file_path=minio_path,
        file_name=file.filename or f"{doc_type.value}.pdf",
        file_size=file_size,
        mime_type=file.content_type or "application/pdf",
        ocr_status=OCRStatus.PENDING,
        processing_status="UPLOADED",
        retry_count=0,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # ── Enqueue OCR task ─────────────────────────────────────────────────────
    try:
        process_document_ocr.delay(str(doc.id))
    except Exception:
        # If Celery worker is offline, OCR can be executed on-demand or retried
        pass

    return DocumentUploadResponse(
        document_id=doc.id,
        file_name=doc.file_name,
        file_size=doc.file_size,
        doc_type=doc.doc_type,
        ocr_status=doc.ocr_status,
        processing_status="UPLOADED",
    )


@router.get(
    "/applications/{app_id}/documents",
    response_model=List[DocumentResponse],
    summary="List all documents for an application",
)
async def list_documents(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[DocumentResponse]:
    """Return all documents associated with an application.

    Args:
        app_id:       Application UUID.
        db:           Async database session.
        current_user: Authenticated user.

    Returns:
        List of :class:`DocumentResponse` objects.
    """
    await _get_application_or_404(app_id, db, current_user)

    result = await db.execute(
        select(Document)
        .where(Document.application_id == app_id)
        .order_by(Document.uploaded_at.asc())
    )
    docs = result.scalars().all()
    return [DocumentResponse.model_validate(d) for d in docs]


@router.get(
    "/documents/{doc_id}",
    response_model=DocumentResponse,
    summary="Get a single document record with extracted data",
)
async def get_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """Retrieve full document info including OCR-extracted fields.

    Args:
        doc_id:       Document UUID.
        db:           Async database session.
        current_user: Authenticated user.

    Returns:
        The :class:`DocumentResponse` for the document.

    Raises:
        :class:`~fastapi.HTTPException` 404: If the document is not found.
    """
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # role-based visibility: institution may only see their own app's docs
    if current_user.role == UserRole.INSTITUTION:
        app_result = await db.execute(
            select(Application).where(Application.id == doc.application_id)
        )
        app = app_result.scalar_one_or_none()
        if app is None or app.institution_id != current_user.institution_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    return DocumentResponse.model_validate(doc)


@router.post(
    "/documents/{doc_id}/retry",
    response_model=DocumentResponse,
    summary="Retry failed OCR and structured claim extraction for a document",
)
async def retry_document_processing(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """Idempotently re-trigger processing for a document that failed or has pending extraction."""
    from app.tasks.ocr_tasks import process_document_ocr
    from app.services.audit_chain import append_chained_audit_log

    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if current_user.role == UserRole.INSTITUTION:
        app_result = await db.execute(
            select(Application).where(Application.id == doc.application_id)
        )
        app = app_result.scalar_one_or_none()
        if app is None or app.institution_id != current_user.institution_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Reset status and increment retry count
    doc.processing_status = "PROCESSING"
    doc.ocr_status = OCRStatus.PROCESSING
    doc.error_message = None
    doc.retry_count = (doc.retry_count or 0) + 1
    doc.updated_at = datetime.now(timezone.utc)
    await db.commit()

    # Append to cryptographic hash-chained audit trail
    await append_chained_audit_log(
        db=db,
        actor=current_user.email,
        action="DOCUMENT_PROCESSING_RETRY",
        application_id=doc.application_id,
        document_id=doc.id,
        result="RETRY_QUEUED",
        notes=f"Extraction retry attempt #{doc.retry_count} initiated for {doc.file_name}",
    )
    await db.commit()

    # Queue or run extraction
    try:
        process_document_ocr.delay(str(doc.id))
    except Exception:
        # Fallback to direct synchronous execution if Celery worker is offline
        from app.services.ocr.extractor import OCRService
        from app.services.ocr.storage import StorageService
        try:
            storage = StorageService()
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                storage.download_file(doc.file_path, tmp.name)
                ocr = OCRService()
                pages_dict, total_pages = ocr.extract_text_by_pages(tmp.name)
                all_text = "\n".join(pages_dict.values())
                doc_type_detected, conf = ocr.classify_document(all_text)
                claims = ocr.extract_structured_claims(pages_dict, doc_type_detected, total_pages)
                doc.extracted_claims = [c.model_dump() for c in claims]
                doc.extracted_data = {
                    "raw_text_length": len(all_text),
                    "total_pages": total_pages,
                    "detected_doc_type": doc_type_detected,
                    "fields": ocr.extract_fields(all_text, doc_type_detected),
                }
                doc.file_hash = ocr.compute_file_hash(tmp.name)
                doc.processing_status = "EXTRACTED"
                doc.ocr_status = OCRStatus.COMPLETE
                await db.commit()
                os.unlink(tmp.name)
        except Exception as sync_err:
            doc.processing_status = "FAILED"
            doc.ocr_status = OCRStatus.FAILED
            doc.error_message = str(sync_err)
            await db.commit()

    await db.refresh(doc)
    return DocumentResponse.model_validate(doc)


@router.get(
    "/applications/{app_id}/cross-document-consistency",
    summary="Cross-Document Consistency Scrutiny Engine",
)
async def get_cross_document_consistency(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Execute cross-document consistency checks comparing extracted claims across all documents.

    Identifies discrepancies in institution name, ID, address, academic year, and intake
    with exact document and page-level provenance.
    """
    from app.services.cross_document import CrossDocumentConsistencyEngine

    await _get_application_or_404(app_id, db, current_user)

    result = await db.execute(
        select(Document).where(Document.application_id == app_id)
    )
    documents = list(result.scalars().all())

    report = CrossDocumentConsistencyEngine.analyze_documents(app_id, documents)
    return report.model_dump()
