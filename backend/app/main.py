"""
main.py — FastAPI Application Entry Point
AICTE AI-Powered Application Validation Platform
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.services.ocr.storage import StorageService

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aicte.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for application startup and shutdown."""
    logger.info("Initializing database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")
    except Exception as exc:
        logger.warning("Could not automatically initialize DB tables: %s", exc)

    logger.info("Ensuring object storage bucket exists...")
    try:
        storage = StorageService()
        storage.ensure_bucket_exists()
        logger.info("Storage bucket '%s' ready.", settings.MINIO_BUCKET)
    except Exception as exc:
        logger.warning("Could not verify/create MinIO bucket at startup: %s", exc)

    yield

    logger.info("Shutting down database engine...")
    await engine.dispose()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description=(
        "AI-Powered Application Validation, Document Authentication "
        "and Regulatory Compliance Verification for AICTE."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── CORS Middleware ────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS if not settings.DEBUG else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include API Routers ────────────────────────────────────────────────────────
app.include_router(api_router)


# ── Root Welcome / Portal Navigation ───────────────────────────────────────────
@app.get(
    "/",
    tags=["System"],
    summary="Platform Entry & Navigation",
)
async def root():
    """Returns a portal landing page with links to Frontend UI, Docs, and Mock APIs."""
    from fastapi.responses import HTMLResponse
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>AICTE AI Validation Platform</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #F8FAFC; color: #1E293B; margin: 0; padding: 40px; display: flex; justify-content: center; }
            .card { background: white; border: 1px solid #E2E8F0; border-radius: 16px; padding: 40px; max-width: 650px; width: 100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
            h1 { color: #1E3A8A; font-size: 24px; margin-top: 0; }
            p { color: #64748B; font-size: 15px; line-height: 1.6; }
            .btn { display: block; padding: 14px 20px; margin: 12px 0; background: #1E3A8A; color: white; text-decoration: none; border-radius: 10px; font-weight: 600; text-align: center; transition: background 0.2s; }
            .btn:hover { background: #1D4ED8; }
            .btn-sec { background: #F1F5F9; color: #1E293B; border: 1px solid #CBD5E1; }
            .btn-sec:hover { background: #E2E8F0; }
            .status { display: inline-block; padding: 4px 10px; background: #DCFCE7; color: #166534; border-radius: 9999px; font-size: 13px; font-weight: 600; }
        </style>
    </head>
    <body>
        <div class="card">
            <span class="status">● All Services Active</span>
            <h1>AICTE AI-Powered Validation Platform</h1>
            <p>Welcome to the AICTE EoA Application Validation, Document Authentication & Regulatory Compliance System.</p>
            
            <a href="http://localhost:3000" class="btn">🚀 Open Web Dashboard (localhost:3000)</a>
            <a href="/docs" class="btn btn-sec">📖 Interactive Backend API Docs (Swagger)</a>
            <a href="http://localhost:8001/docs" class="btn btn-sec">🏛️ Mock Issuing Authorities API (DigiLocker/NAAC/NOC)</a>
            <a href="/health" class="btn btn-sec">🩺 System Health Status</a>

            <div style="margin-top: 25px; padding-top: 20px; border-top: 1px solid #E2E8F0; font-size: 13px; color: #94A3B8;">
                <strong>Demo Credentials:</strong><br>
                • Officer: <code>officer@demo.com</code> / <code>Demo@1234</code><br>
                • Institution: <code>institution@demo.com</code> / <code>Demo@1234</code>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ── Health Check ───────────────────────────────────────────────────────────────
@app.get(
    "/health",
    tags=["System"],
    summary="Service Health Check",
    status_code=status.HTTP_200_OK,
)
async def health_check() -> dict:
    """Returns application status, version, and basic environment info."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "debug": settings.DEBUG,
    }


# ── Global Exception Handlers ──────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "message": "Input validation failed. Please check the submitted fields.",
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception("Unhandled server error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": "An internal server error occurred.",
            "detail": str(exc) if settings.DEBUG else "Please contact support.",
        },
    )
