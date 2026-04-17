from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time
from .routers import runs, tasks
from .routers.hitl import router as hitl_router
from ...infrastructure.database.connection import DatabaseConnection
from ...infrastructure.observability.tracer import OTelTracer
from ...config import get_settings
from core.errors.exceptions import EvalFrameworkError, RunNotFoundError, SafetyViolationError, InfrastructureError

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await DatabaseConnection.initialise(settings.database_url)
    OTelTracer.initialise(settings.otel_service_name, settings.otel_endpoint)
    yield
    await DatabaseConnection.close()

app = FastAPI(lifespan=lifespan, title="Eval Core API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time_ms = (time.time() - start_time) * 1000
    response.headers["X-Response-Time-Ms"] = str(int(process_time_ms))
    return response

@app.exception_handler(RunNotFoundError)
async def not_found_exception_handler(request: Request, exc: RunNotFoundError):
    return JSONResponse(status_code=404, content={"message": str(exc)})

@app.exception_handler(SafetyViolationError)
async def safety_exception_handler(request: Request, exc: SafetyViolationError):
    return JSONResponse(status_code=400, content={"message": str(exc), "must_not_contain": getattr(exc, 'must_not_contain', '')})

@app.exception_handler(InfrastructureError)
async def infra_exception_handler(request: Request, exc: InfrastructureError):
    return JSONResponse(status_code=503, content={"message": str(exc)})

# Catchall Eval error
@app.exception_handler(EvalFrameworkError)
async def framework_exception_handler(request: Request, exc: EvalFrameworkError):
    return JSONResponse(status_code=422, content={"message": str(exc)})

app.include_router(runs.router)
app.include_router(tasks.router)
app.include_router(hitl_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
