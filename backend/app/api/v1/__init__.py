"""
API v1 router assembly.
"""

from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.applications import router as applications_router
from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.metrics import router as metrics_router
from app.api.v1.routes.infrastructure import router as infrastructure_router
from app.api.v1.routes.public_verify import router as public_verify_router
from app.api.v1.routes.campus_geo import router as campus_geo_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(applications_router)
api_router.include_router(documents_router)
api_router.include_router(metrics_router)
api_router.include_router(infrastructure_router)
api_router.include_router(public_verify_router)
api_router.include_router(campus_geo_router)
