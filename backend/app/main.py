# backend/app/main.py
"""
FastAPI application entry point — PromptVault MVP.
All configuration from environment; no hardcoded values.
"""
from __future__ import annotations

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("promptvault")

settings = get_settings()

app = FastAPI(
    title="PromptVault",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)


# ── Global Error Handler ─────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — returns a clean 500 with detail."""
    logger.error(
        "Unhandled exception on %s %s: %s\n%s",
        request.method,
        request.url.path,
        exc,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Map ValueError from services to HTTP 400."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}
