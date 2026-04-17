"""HITL review queue endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ....infrastructure.database.connection import DatabaseConnection
from ....infrastructure.database.repositories.postgres_run_repository import PostgresRunRepository
from ....infrastructure.database.repositories.postgres_trajectory_repository import PostgresTrajectoryRepository
from ....infrastructure.regression.generator import RegressionTestGenerator
from ....domain.entities.task import Task, CheckpointVO
from core.errors.exceptions import RunNotFoundError

router = APIRouter(prefix="/hitl", tags=["hitl"])


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class AnnotateRequest(BaseModel):
    root_cause: str   # bad_plan | wrong_tool | wrong_tool_args | hallucination | prompt_injection | tool_error | other
    severity: str     # critical | major | minor
    notes: str = ""
    tags: list[str] = []
    annotator: str = "reviewer"


class AnnotateResponse(BaseModel):
    annotated: bool
    golden_set_id: str
    regression_test_path: str


# ── Dependency ───────────────────────────────────────────────────────────────

async def _db():
    async with DatabaseConnection.get_session() as session:
        yield session


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/queue")
async def get_queue(
    limit: int = 50,
    session: AsyncSession = Depends(_db),
):
    """Return failed EvalRuns that have not yet been annotated."""
    run_repo = PostgresRunRepository(session)
    runs = await run_repo.list(limit=limit, status="FAIL")
    return [
        {
            "run_id": r.run_id,
            "task_id": r.task_id,
            "status": r.status.value if hasattr(r.status, "value") else r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "score": r.score,
        }
        for r in runs
    ]


@router.get("/{run_id}/replay")
async def get_replay(
    run_id: str,
    session: AsyncSession = Depends(_db),
):
    """Return full conversation data for a failed run for HITL annotation."""
    run_repo = PostgresRunRepository(session)
    traj_repo = PostgresTrajectoryRepository(session)

    run = await run_repo.get_by_id(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    trajectory = await traj_repo.get_by_run_id(run_id)

    return {
        "run_id": run_id,
        "task_id": run.task_id,
        "status": run.status.value if hasattr(run.status, "value") else run.status,
        "trajectory_spans": trajectory.to_dict().get("spans", []) if trajectory else [],
        "final_output": trajectory.final_output if trajectory else "",
        "step_count": trajectory.step_count if trajectory else 0,
        "tool_names_called": trajectory.tool_names_called if trajectory else [],
        "error_count": trajectory.error_count if trajectory else 0,
    }


@router.post("/{run_id}/annotate", response_model=AnnotateResponse)
async def annotate_run(
    run_id: str,
    request: AnnotateRequest,
    session: AsyncSession = Depends(_db),
):
    """Annotate a failed run, write a GoldenSet row, and generate a regression test."""
    run_repo = PostgresRunRepository(session)
    traj_repo = PostgresTrajectoryRepository(session)

    run = await run_repo.get_by_id(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    trajectory = await traj_repo.get_by_run_id(run_id)
    if trajectory is None:
        raise HTTPException(status_code=404, detail=f"Trajectory for run '{run_id}' not found")

    golden_set_id = str(uuid.uuid4())[:8]

    # Persist GoldenSet row
    from infrastructure.db.models import GoldenSetModel
    golden = GoldenSetModel(
        annotation_id=golden_set_id,
        task_id=run.task_id,
        trajectory_hash=trajectory.trajectory_hash,
        is_regression=True,
        human_score=None,
        notes=request.notes,
        created_at=datetime.now(timezone.utc),
    )
    session.add(golden)
    await session.flush()

    # Build a minimal Task entity for the regression generator
    task = Task(
        task_id=run.task_id,
        name=run.task_id,
        description="",
        prompt="",
        expected_outcome="",
        category="BASIC_QA",  # type: ignore[arg-type]
        checkpoints=(),
        max_steps=10,
        min_steps=1,
        perturbations=(),
        tags=frozenset(request.tags),
    )

    annotation = {
        "root_cause": request.root_cause,
        "severity": request.severity,
        "notes": request.notes,
        "tags": request.tags,
        "annotator": request.annotator,
        "golden_set_id": golden_set_id,
    }

    generator = RegressionTestGenerator()
    test_path = generator.generate(task, trajectory, annotation)

    return AnnotateResponse(
        annotated=True,
        golden_set_id=golden_set_id,
        regression_test_path=str(test_path),
    )

