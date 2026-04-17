from fastapi import FastAPI
from contextlib import asynccontextmanager
from .routers import metrics

@asynccontextmanager
async def lifespan(app: FastAPI):
    from infrastructure.db.connection import DatabaseConnection
    import os
    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/agent_eval")
    await DatabaseConnection.initialise(db_url)
    yield
    await DatabaseConnection.close()

app = FastAPI(lifespan=lifespan, title="Metrics Service", version="1.0.0")

app.include_router(metrics.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
