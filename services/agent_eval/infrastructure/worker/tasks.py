"""Celery tasks for the eval-core worker.

Each task runs an async eval suite inside a new event loop, reports
incremental progress to Redis, and stores the final result as a Celery
task result.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import redis

from services.agent_eval.infrastructure.worker.celery_app import app


def _redis_client() -> redis.Redis:
    return redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)


@app.task(bind=True, name="run_eval_suite", track_started=True)
def run_eval_suite_task(
    self,
    task_ids: list[str] | str,
    category: str | None,
    agent_version: str,
    job_id: str,
) -> dict[str, Any]:
    """Execute an eval suite in a Celery worker process.

    Progress is written to Redis key ``eval:job:{job_id}:progress`` every
    time a task completes so the SSE endpoint can stream it to clients.

    Returns a dict with final ``job_id``, ``pass_rate``, and ``total`` fields.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _run_suite_async(task_ids, category, agent_version, self, job_id)
        )
        return result
    finally:
        loop.close()


async def _run_suite_async(
    task_ids: list[str] | str,
    category: str | None,
    agent_version: str,
    celery_task,
    job_id: str,
) -> dict[str, Any]:
    """Async body of the Celery task — initialises DB/OTel, runs suite."""
    from services.agent_eval.config import get_settings
    from services.agent_eval.infrastructure.database.connection import DatabaseConnection
    from services.agent_eval.infrastructure.observability.tracer import OTelTracer
    from services.agent_eval.container import Container

    settings = get_settings()
    await DatabaseConnection.initialise(settings.database_url)
    OTelTracer.initialise(settings.otel_service_name, settings.otel_endpoint)

    container = Container(settings)
    r = _redis_client()

    completed = 0

    async def progress_callback(task, run, completed_count, total):
        nonlocal completed
        completed = completed_count
        progress_data = {
            "completed": completed_count,
            "total": total,
            "last_task": task.name,
            "last_status": run.status.value if hasattr(run.status, "value") else run.status,
        }
        r.setex(f"eval:job:{job_id}:progress", 3600, json.dumps(progress_data))
        celery_task.update_state(
            state="PROGRESS",
            meta=progress_data,
        )

    # Build a fully-wired EvalService using a live DB session
    async with DatabaseConnection.get_session() as session:
        eval_service = await container.build_eval_service(session)
        result = await eval_service.run_suite(task_ids, category, agent_version)

    runs = result.get("runs", [])
    passed = sum(1 for run in runs if run.get("status") == "PASS")
    total = len(runs)
    pass_rate = passed / max(1, total)

    final = {"job_id": job_id, "pass_rate": pass_rate, "total": total, "completed": True}
    r.setex(f"eval:job:{job_id}:result", 3600, json.dumps(final))
    return final

