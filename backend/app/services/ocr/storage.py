"""
MinIO object storage service for document file management.
"""

from __future__ import annotations

import os
import shutil
import logging
from datetime import timedelta
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger("aicte.storage")


class StorageService:
    """Wraps MinIO / S3-compatible object storage with local filesystem fallback."""

    def __init__(self) -> None:
        """Initialise a boto3 client connected to MinIO using application settings."""
        self._client = boto3.client(
            "s3",
            endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(
                signature_version="s3v4",
                connect_timeout=1,
                read_timeout=1,
                retries={"max_attempts": 1},
            ),
            region_name="us-east-1",
        )
        self._bucket = settings.MINIO_BUCKET
        self._local_storage_root = Path(__file__).resolve().parents[3] / "uploads"
        self._local_storage_root.mkdir(parents=True, exist_ok=True)

    def ensure_bucket_exists(self) -> None:
        """Create the configured bucket if it does not already exist."""
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except Exception as exc:
            try:
                self._client.create_bucket(Bucket=self._bucket)
            except Exception:
                logger.info("MinIO service not reachable; fallback to local disk storage at %s", self._local_storage_root)

    def upload_file(
        self,
        local_path: str,
        application_id: str,
        doc_type: str,
        filename: str,
    ) -> str:
        """Upload a local file to MinIO (or fallback to local disk storage)."""
        object_key = f"applications/{application_id}/{doc_type}/{filename}"
        try:
            self._client.upload_file(local_path, self._bucket, object_key)
            return object_key
        except Exception as exc:
            logger.warning("MinIO upload failed (%s). Saving to local storage.", exc)
            dest = self._local_storage_root / "applications" / str(application_id) / str(doc_type) / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_path, dest)
            return str(dest)

    def download_file(self, file_path: str, local_dest: str) -> str:
        """Download an object from MinIO to a local destination path.

        Args:
            file_path:  The MinIO object key to download.
            local_dest: Local absolute path where the file should be saved.

        Returns:
            The ``local_dest`` path after the download completes.
        """
        dest = Path(local_dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        self._client.download_file(self._bucket, file_path, str(dest))
        return str(dest)

    def get_presigned_url(self, file_path: str, expires: int = 3600) -> str:
        """Generate a time-limited pre-signed URL for direct file access.

        Args:
            file_path: The MinIO object key.
            expires:   URL validity in seconds (default: 1 hour).

        Returns:
            A pre-signed HTTPS URL string.
        """
        url: str = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": file_path},
            ExpiresIn=expires,
        )
        return url
