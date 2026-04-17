"""Eval run endpoints: trigger, list, detail, trace, and SSE stream."""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from ....application.services.eval_service import EvalService
from ..deps import get_eval_service
from ...schemas.run_schemas import (
    CreateRunRequest,
    EdgeData,
    NodeData,
    ReactFlowResponse,
    RunDetailResponse,
    RunSummaryResponse,
    SpanResponse,
    TrajectoryResponse,
)

router = APIRouter(prefix="/runs", tags=["runs"])

# Poll interval for Redis-backed SSE streaming (seconds)
_SSE_POLL_INTERVAL = 0.5


# ── Helper ───────────────────────────────────────────────────────────────────

def _redis_client():
    import redis as _redis
    return _redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True
    )


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/", status_code=202)
async def create_run(
    request: CreateRunRequest,
    eval_service: EvalService = Depends(get_eval_service),
) -> dict:
    """Enqueue an eval suite via Celery.  Returns immediately with a job_id."""
    from services.agent_eval.infrastructure.worker.tasks import run_eval_suite_task

    job_id = str(uuid.uuid4())
    celery_job = run_eval_suite_task.delay(
        request.task_ids,
        request.category,
        request.agent_version,
        job_id,
    )
    return {"job_id": job_id, "celery_task_id": celery_job.id, "status": "queued"}


@router.get("/", response_model=List[RunSummaryResponse])
async def list_runs(
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    eval_service: EvalService = Depends(get_eval_service),
) -> List[RunSummaryResponse]:
    """Return the most recent eval runs, optionally filtered by status."""
    runs = await eval_service.list_runs(limit, offset, status)
    return [
        RunSummaryResponse(
            run_id=r.run_id,
            task_id=r.task_id,
            agent_version=r.agent_version,
            status=r.status.value if hasattr(r.status, "value") else r.status,
            created_at=r.started_at,
            score=r.score,
            duration_ms=r.duration_ms,
        )
        for r in runs
    ]


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run_detail(
    run_id: str,
    eval_service: EvalService = Depends(get_eval_service),
) -> RunDetailResponse:
    """Return full detail for a single run including its trajectory."""
    run = await eval_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    traj_resp = None
    if run.trajectory:
        spans_resp = [
            SpanResponse(
                span_type=s.span_type,
                span_id=s.span_id,
                duration_ms=s.duration_ms,
                attributes=s.attributes,
                error=s.error,
            )
            for s in run.trajectory.spans
        ]
        traj_resp = TrajectoryResponse(
            spans=spans_resp,
            step_count=run.trajectory.step_count,
            token_total=run.trajectory.token_total,
            duration_ms=run.trajectory.duration_ms,
            tool_names_called=run.trajectory.tool_names_called,
            error_count=run.trajectory.error_count,
        )

    return RunDetailResponse(
        run_id=run.run_id,
        task_id=run.task_id,
        status=run.status.value if hasattr(run.status, "value") else run.status,
        trajectory=traj_resp,
        judge_scores=None,
    )


@router.get("/{run_id}/trace", response_model=ReactFlowResponse)
async def get_run_trace(
    run_id: str,
    eval_service: EvalService = Depends(get_eval_service),
) -> ReactFlowResponse:
    """Convert a run's trajectory into React Flow nodes and edges."""
    run = await eval_service.get_run(run_id)
    if not run or not run.trajectory:
        raise HTTPException(status_code=404, detail=f"Trace for run '{run_id}' not found")

    _type_map = {
        "LLM_CALL": "llm_call",
        "TOOL_CALL": "tool_call",
        "CHAIN_STEP": "chain_step",
    }

    nodes: list[NodeData] = []
    edges: list[EdgeData] = []
    prev_id: Optional[str] = None

    for span in run.trajectory.spans:
        node_type = "error" if span.error else _type_map.get(span.span_type, "chain_step")
        label = (
            span.attributes.get("tool_name", span.span_type)
            if node_type in ("tool_call", "error")
            else f"{span.attributes.get('tokens_total', 0)} tok"
        )
        nodes.append(
            NodeData(
                id=span.span_id,
                type=node_type,
                data={"label": label, "duration_ms": span.duration_ms, "attributes": span.attributes},
            )
        )
        if prev_id:
            edges.append(EdgeData(source=prev_id, target=span.span_id))
        prev_id = span.span_id

    return ReactFlowResponse(nodes=nodes, edges=edges)


@router.get("/{run_id}/stream")
async def stream_run_progress(run_id: str):
    """SSE endpoint that streams eval progress polled from Redis."""

    async def event_generator() -> AsyncGenerator[dict, None]:
        r = _redis_client()
        sent_done = False
        timeout_ticks = int(300 / _SSE_POLL_INTERVAL)  # 5-minute max stream

        for _ in range(timeout_ticks):
            if sent_done:
                break

            # Check progress
            raw_progress = r.get(f"eval:job:{run_id}:progress")
            if raw_progress:
                progress = json.loads(raw_progress)
                yield {
                    "event": "progress",
                    "data": json.dumps(
                        {
                            "type": "progress",
                            "completed": progress.get("completed", 0),
                            "total": progress.get("total", 0),
                            "last_task": progress.get("last_task", ""),
                        }
                    ),
                }

            # Check completion
            raw_result = r.get(f"eval:job:{run_id}:result")
            if raw_result:
                result = json.loads(raw_result)
                yield {
                    "event": "suite_complete",
                    "data": json.dumps(
                        {
                            "type": "suite_complete",
                            "pass_rate": result.get("pass_rate", 0.0),
                            "total": result.get("total", 0),
                        }
                    ),
                }
                sent_done = True
                break

            await asyncio.sleep(_SSE_POLL_INTERVAL)

        if not sent_done:
            yield {"event": "error", "data": json.dumps({"type": "error", "message": "Stream timeout"})}

    return EventSourceResponse(event_generator())
