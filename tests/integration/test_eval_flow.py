"""Integration tests for the full eval pipeline."""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

from services.agent_eval.domain.entities.task import Task, CheckpointVO
from services.agent_eval.application.use_cases.run_eval_task import RunEvalTaskUseCase
from core.domain.types import RunStatus


@pytest.mark.integration
@pytest.mark.asyncio
class TestEvalFlow:
    """End-to-end tests that exercise the real infrastructure layers."""

    async def test_run_single_task_creates_trajectory(
        self, agent_factory, run_repo, traj_repo, event_bus
    ):
        """Run one task; verify EvalRun and Trajectory are persisted."""
        task = Task(
            task_id="test_calc_001",
            name="calc_test",
            description="Basic arithmetic verification",
            prompt="What is 6 * 7? Use the calculator tool and return the result.",
            expected_outcome="42",
            category="TOOL_USE",  # type: ignore[arg-type]
            checkpoints=(
                CheckpointVO(
                    step=1,
                    tool_called="calculator",
                    output_contains="42",
                    must_not_contain=None,
                    description="Must use calculator and produce 42",
                ),
            ),
            max_steps=5,
            min_steps=1,
            perturbations=(),
            tags=frozenset(["integration"]),
        )

        use_case = RunEvalTaskUseCase(
            agent_factory=agent_factory,
            run_repo=run_repo,
            traj_repo=traj_repo,
            event_bus=event_bus,
            timeout_seconds=60,
        )
        run = await use_case.execute(task)

        # Run must reach a terminal status
        assert run.status in (RunStatus.PASS, RunStatus.FAIL, RunStatus.ERROR), (
            f"Unexpected status: {run.status}"
        )

        # Trajectory must be saved
        saved_traj = await traj_repo.get_by_run_id(run.run_id)
        assert saved_traj is not None, "Trajectory was not persisted to DB"
        assert saved_traj.step_count > 0, "Trajectory has no spans"

    async def test_judge_service_rule_evaluation(self, httpx_client):
        """POST to the judge service evaluate endpoint; expect valid scores."""
        task_payload = {
            "task_id": "test_001",
            "name": "test",
            "description": "",
            "prompt": "What is 2+2?",
            "expected_outcome": "4",
            "category": "BASIC_QA",
            "checkpoints": [{"step": 1, "output_contains": "4"}],
            "max_steps": 5,
            "min_steps": 1,
            "perturbations": [],
            "tags": [],
        }
        traj_payload = {
            "trajectory_id": "traj-001",
            "run_id": "run-001",
            "spans": [],
            "final_output": "The answer is 4.",
            "created_at": "2026-01-01T00:00:00",
        }

        resp = await httpx_client.post(
            "http://localhost:8001/judge/evaluate",
            json={
                "task": task_payload,
                "trajectory": traj_payload,
                "final_output": "The answer is 4.",
                "strategy": "rule",
            },
        )
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code} — {resp.text}"
        data = resp.json()
        assert 0.0 <= data["score"] <= 1.0, "Score out of range"
        assert "rationale" in data

    async def test_gateway_routes_to_eval_core(self, httpx_client, auth_token):
        """Gateway /api/runs → eval-core /runs — must return a list."""
        resp = await httpx_client.get(
            "http://localhost:8080/api/runs",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200, f"Gateway routing failed: {resp.text}"
        assert isinstance(resp.json(), list)

    async def test_hitl_annotation_creates_regression_test(
        self, run_repo, traj_repo, db_session, tmp_path
    ):
        """Annotate a FAIL run; verify GoldenSet row and regression test file."""
        from datetime import datetime, timezone
        from services.agent_eval.domain.entities.eval_run import EvalRun
        from services.agent_eval.domain.entities.trajectory import Trajectory
        from services.agent_eval.domain.entities.span import Span
        from core.domain.types import RunStatus
        from services.agent_eval.infrastructure.regression.generator import RegressionTestGenerator

        # Persist a failed run
        run = EvalRun(
            run_id="hitl-test-001",
            task_id="hitl-task-001",
            agent_version="v1.0",
            status=RunStatus.FAIL,
            started_at=datetime.now(timezone.utc),
        )
        run.complete(RunStatus.FAIL, "rule check: missing tool call")
        await run_repo.save(run)

        span = Span(
            span_id="span-001",
            trace_id="trace-001",
            span_type="LLM_CALL",
            start_time=0.0,
            end_time=0.5,
            attributes={"tokens_total": 100},
            error=False,
            error_message=None,
        )
        trajectory = Trajectory(
            trajectory_id="traj-hitl-001",
            run_id="hitl-test-001",
            spans=[span],
            final_output="wrong answer",
            created_at=datetime.now(timezone.utc),
        )
        await traj_repo.save(trajectory, "hitl-test-001")

        from services.agent_eval.domain.entities.task import Task
        task = Task(
            task_id="hitl-task-001",
            name="hitl_task",
            description="HITL test task",
            prompt="What is 2+2?",
            expected_outcome="4",
            category="BASIC_QA",  # type: ignore[arg-type]
            checkpoints=(),
            max_steps=5,
            min_steps=1,
            perturbations=(),
            tags=frozenset(),
        )
        annotation = {
            "root_cause": "wrong_tool",
            "severity": "major",
            "notes": "Agent called wrong tool",
            "golden_set_id": "abc123",
        }

        generator = RegressionTestGenerator(output_dir=tmp_path)
        test_path = generator.generate(task, trajectory, annotation)

        assert test_path.exists(), f"Regression test file not created at {test_path}"
        content = test_path.read_text()
        assert "pytest.mark.regression" in content
        assert "hitl-task-001" in content

    async def test_sse_stream_returns_events(self, httpx_client, auth_token):
        """Trigger a run then connect to SSE; expect at least a progress or error event."""
        # Trigger a run
        create_resp = await httpx_client.post(
            "http://localhost:8080/api/runs",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"task_ids": ["test_calc_001"], "agent_version": "v1.0"},
        )
        assert create_resp.status_code == 202
        job_id = create_resp.json()["job_id"]

        # Connect to SSE stream and collect events for up to 15s
        collected = []
        async with httpx_client.stream(
            "GET",
            f"http://localhost:8080/api/runs/{job_id}/stream",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Accept": "text/event-stream",
            },
            timeout=20,
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    collected.append(line)
                if len(collected) >= 1:
                    break

        assert len(collected) >= 1, "SSE stream produced no events"
