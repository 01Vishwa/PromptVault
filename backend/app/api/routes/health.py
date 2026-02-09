"""
Health Check Routes
==================

System health and status endpoints.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime

from app.config import settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    environment: str
    timestamp: str
    version: str
    providers: Dict[str, bool]


class ReadinessResponse(BaseModel):
    """Readiness check response."""
    ready: bool
    checks: Dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint.
    
    Returns:
        Health status of the application
    """
    return HealthResponse(
        status="healthy",
        environment=settings.environment,
        timestamp=datetime.utcnow().isoformat(),
        version="0.1.0",
        providers={
            "nvidia": bool(settings.nvidia_api_key),
            "github": bool(settings.github_token),
            "tavily": bool(settings.tavily_api_key)
        }
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """Readiness check - verifies all dependencies.
    
    Returns:
        Readiness status with individual checks
    """
    checks = {
        "config_loaded": True,
        "nvidia_configured": bool(settings.nvidia_api_key),
        "github_configured": bool(settings.github_token),
        "tavily_configured": bool(settings.tavily_api_key)
    }
    
    # Ready if at least one LLM provider is configured
    llm_ready = checks["nvidia_configured"] or checks["github_configured"]
    
    return ReadinessResponse(
        ready=llm_ready,
        checks=checks
    )
