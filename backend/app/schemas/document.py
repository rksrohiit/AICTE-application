"""
Pydantic v2 schemas for document-related API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel

from app.models.document import DocumentType, OCRStatus


class DocumentResponse(BaseModel):
    """Full document record returned by the API."""

    id: uuid.UUID
    application_id: uuid.UUID
    doc_type: DocumentType
    file_name: str
    file_size: int
    mime_type: str
    ocr_status: OCRStatus
    extracted_data: Dict[str, Any] | None
    file_hash: str | None
    uploaded_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    """Immediate response returned after a successful document upload."""

    document_id: uuid.UUID
    file_name: str
    file_size: int
    doc_type: DocumentType
    ocr_status: OCRStatus
    message: str = "Document uploaded successfully. OCR processing queued."
