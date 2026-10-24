"""Minimal live API workflow coverage.

These tests intentionally run against PostgreSQL, the supported application
database. They exercise the same HTTP paths used by the frontend and stub only
external object storage and Celery dispatch.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.institution import InstitutionRecord


pytestmark = pytest.mark.integration


def _postgres_is_configured() -> bool:
    value = os.getenv("DATABASE_URL", "")
    return value.startswith(("postgresql://", "postgres://"))


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _postgres_is_configured(),
        reason="Set DATABASE_URL to a PostgreSQL instance to run API integration tests",
    ),
]


def _create_institution() -> str:
    institution_id = uuid.uuid4()

    async def create() -> None:
        async with AsyncSessionLocal() as session:
            session.add(
                InstitutionRecord(
                    id=institution_id,
                    aicte_id=f"TEST-{institution_id.hex[:10]}",
                    name="Integration Test Institute",
                    state="Maharashtra",
                    district="Pune",
                    approved_intake=120,
                    approved_programmes=["Computer Engineering"],
                )
            )
            await session.commit()

    asyncio.run(create())
    return str(institution_id)


def test_institution_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    institution_id = _create_institution()
    email = f"api-test-{uuid.uuid4().hex[:8]}@example.com"
    password = "Integration@123"

    class FakeStorage:
        def ensure_bucket_exists(self) -> None:
            return None

        def upload_file(self, **_: object) -> str:
            return "applications/test/document.pdf"

    monkeypatch.setattr("app.services.ocr.storage.StorageService", FakeStorage)

    with TestClient(app) as client:
        register = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": "Integration User",
                "institution_id": institution_id,
            },
        )
        assert register.status_code == 201, register.text

        login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        application = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "institution_name": "Integration Test Institute",
                "application_type": "EOA_RENEWAL",
                "academic_year": "2026-27",
                "programmes": ["Computer Engineering"],
            },
        )
        assert application.status_code == 201, application.text
        application_id = application.json()["id"]

        listed = client.get("/api/v1/applications", headers=headers)
        assert listed.status_code == 200
        assert listed.json()["total"] >= 1

        upload = client.post(
            f"/api/v1/applications/{application_id}/documents",
            headers=headers,
            files={
                "file": (
                    "affidavit.pdf",
                    b"%PDF-1.4 integration test",
                    "application/pdf",
                )
            },
            data={"doc_type": "AFFIDAVIT"},
        )
        assert upload.status_code == 201, upload.text

        monkeypatch.setattr(
            "app.tasks.validation_tasks.run_validation.delay",
            lambda _: type("Task", (), {"id": "integration-task"})(),
        )
        validation = client.post(
            f"/api/v1/applications/{application_id}/validate",
            headers=headers,
        )
        assert validation.status_code == 202, validation.text
        assert validation.json()["task_id"] == "integration-task"
