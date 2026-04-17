from fastapi import APIRouter, Depends
from typing import List
from ...infrastructure.database.metrics_repository import MetricsRepository
from ...domain.entities.metrics import SuiteMetrics
import random

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Scaffolding dependency
async def get_metrics_repo():
    from infrastructure.db.connection import DatabaseConnection
    async with DatabaseConnection.get_session() as session:
        yield MetricsRepository(session)

@router.get("/summary", response_model=dict)
async def get_summary(repo: MetricsRepository = Depends(get_metrics_repo)):
    metrics = await repo.compute_suite_metrics([])
    d = metrics.__dict__.copy()
    d["run_timestamp"] = d["run_timestamp"].isoformat()
    return d

@router.get("/history", response_model=List[dict])
async def get_history(days: int = 7, repo: MetricsRepository = Depends(get_metrics_repo)):
    history = await repo.get_history(days)
    ret = []
    for m in history:
        d = m.__dict__.copy()
        d["run_timestamp"] = d["run_timestamp"].isoformat()
        ret.append(d)
    return ret

@router.get("/regression")
async def check_regression(repo: MetricsRepository = Depends(get_metrics_repo)):
    return {"detected": False, "delta": None, "regressed_tasks": []}

@router.get("/alerts")
async def get_alerts(repo: MetricsRepository = Depends(get_metrics_repo)):
    return await repo.get_active_alerts()
