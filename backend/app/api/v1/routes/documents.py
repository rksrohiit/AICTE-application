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

    # ── MIME type guard ──────────────────────────────────────────────────────
    if file.content_type not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: {sorted(_ALLOWED_MIME_TYPES)}",
        )

    # ── Read and size-check the file ─────────────────────────────────────────
    file_bytes = await file.read()
    file_size = len(file_bytes)
    if file_size > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {_MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
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
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # ── Enqueue OCR task ─────────────────────────────────────────────────────
    process_document_ocr.delay(str(doc.id))

    return DocumentUploadResponse(
        document_id=doc.id,
        file_name=doc.file_name,
        file_size=doc.file_size,
        doc_type=doc.doc_type,
        ocr_status=doc.ocr_status,
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
