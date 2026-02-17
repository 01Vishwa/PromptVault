# backend/app/api/v1/__init__.py
"""API v1 router aggregation."""
from fastapi import APIRouter

from app.api.v1.deployments import router as deployments_router
from app.api.v1.execute import router as execute_router
from app.api.v1.prompts import router as prompts_router
from app.api.v1.serve import router as serve_router
from app.api.v1.versions import router as versions_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(prompts_router)
api_router.include_router(versions_router)
api_router.include_router(execute_router)
api_router.include_router(deployments_router)
api_router.include_router(serve_router)
