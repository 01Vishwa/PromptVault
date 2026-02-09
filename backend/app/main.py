"""
Axiom AI — FastAPI Main Application
====================================

Entry point for the Axiom AI backend server.
Configures FastAPI with middleware, routes, and lifecycle handlers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import time

from app.config import settings
from app.api.routes import health, chat
from app.llm.client import cleanup_llm_client

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "Starting Axiom AI",
        environment=settings.environment,
        debug=settings.debug
    )
    
    yield
    
    # Shutdown
    logger.info("Shutting down Axiom AI")
    await cleanup_llm_client()


# Create FastAPI application
app = FastAPI(
    title="Axiom AI",
    description="An agentic search engine with ReACT, ReWOO, and multi-agent capabilities",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)


# =============================================================================
# Middleware
# =============================================================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    """Add request timing to response headers."""
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.info(
        "Request",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else "unknown"
    )
    response = await call_next(request)
    return response


# =============================================================================
# Exception Handlers
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        error=str(exc),
        exc_info=exc
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
            "details": str(exc) if settings.debug else None
        }
    )


# =============================================================================
# Routes
# =============================================================================

# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": "Axiom AI",
        "version": "0.1.0",
        "description": "Agentic search engine with multi-step reasoning",
        "docs": "/docs" if settings.debug else None,
        "health": "/api/v1/health"
    }


# =============================================================================
# Development Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
