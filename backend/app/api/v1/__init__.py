"""
API v1 router assembly.
"""

from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.applications import router as applications_router
from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.metrics import router as metrics_router
from app.api.v1.routes.infrastructure import router as infrastructure_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(applications_router)
api_router.include_router(documents_router)
api_router.include_router(metrics_router)
api_router.include_router(infrastructure_router)
