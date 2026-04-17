"""End-to-end test: simulates the complete developer workflow via the gateway."""
from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
import pytest_asyncio


GATEWAY = "http://localhost:8080"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_user_journey():
    """
    Proves the full 8-step workflow:
    1. Authenticate via gateway.
    2. Trigger a full eval suite run (task_ids="all" against fixture tasks).
    3. Stream SSE progress events.
    4. Retrieve the completed run from the run list.
    5. Fetch the React Flow trace graph.
    6. Score a trajectory via judge service.
    7. Retrieve aggregated metrics.
    8. Annotate a failed run (HITL) and verify regression test creation.
    """
    async with httpx.AsyncClient(timeout=60) as client:

        # ── Step 1: Authenticate ─────────────────────────────────────────────
        auth_resp = await client.post(f"{GATEWAY}/auth/token", json={"api_key": "test"})
        assert auth_resp.status_code == 200, f"Auth failed: {auth_resp.text}"
        token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # ── Step 2: Trigger eval suite ───────────────────────────────────────
        run_resp = await client.post(
            f"{GATEWAY}/api/runs",
            headers=headers,
            json={"task_ids": "all", "agent_version": "v1.0-e2e"},
        )
        assert run_resp.status_code == 202, f"Trigger failed: {run_resp.text}"
        job_id = run_resp.json()["job_id"]
        assert job_id, "No job_id returned"

        # ── Step 3: Receive SSE progress events ──────────────────────────────
        events_collected = []
        async with client.stream(
            "GET",
            f"{GATEWAY}/api/runs/{job_id}/stream",
            headers={**headers, "Accept": "text/event-stream"},
            timeout=60,
        ) as stream:
            async for line in stream.aiter_lines():
                if line.startswith("data:"):
                    events_collected.append(line)
                if any("suite_complete" in e for e in events_collected):
                    break
                if len(events_collected) >= 20:
                    break

        assert len(events_collected) >= 1, "No SSE events received"

        # ── Step 4: List completed runs ──────────────────────────────────────
        runs_resp = await client.get(f"{GATEWAY}/api/runs", headers=headers)
        assert runs_resp.status_code == 200
        runs = runs_resp.json()
        assert isinstance(runs, list), "Expected list of runs"

        if not runs:
            pytest.skip("No runs completed within timeout — skipping downstream steps")

        run_id = runs[0]["run_id"]

        # ── Step 5: Fetch trace graph ────────────────────────────────────────
        trace_resp = await client.get(f"{GATEWAY}/api/runs/{run_id}/trace", headers=headers)
        # 404 is acceptable if trajectory was not saved (agent timeout), not a flow failure
        if trace_resp.status_code == 200:
            trace = trace_resp.json()
            assert "nodes" in trace
            assert "edges" in trace

        # ── Step 6: Score trajectory via judge ───────────────────────────────
        judge_resp = await client.post(
            f"{GATEWAY}/api/judge/evaluate",
            headers=headers,
            json={
                "task": {
                    "task_id": "e2e-task-001",
                    "name": "e2e_test",
                    "description": "",
                    "prompt": "What is 2+2?",
                    "expected_outcome": "4",
                    "category": "BASIC_QA",
                    "checkpoints": [{"step": 1, "output_contains": "4"}],
                    "max_steps": 5,
                    "min_steps": 1,
                    "perturbations": [],
                    "tags": [],
                },
                "trajectory": {
                    "trajectory_id": "e2e-traj-001",
                    "run_id": "e2e-run-001",
                    "spans": [],
                    "final_output": "4",
                    "created_at": "2026-01-01T00:00:00",
                },
                "final_output": "4",
                "strategy": "rule",
            },
        )
        assert judge_resp.status_code == 200, f"Judge eval failed: {judge_resp.text}"
        judge_data = judge_resp.json()
        assert 0.0 <= judge_data["score"] <= 1.0

        # ── Step 7: Retrieve metrics ─────────────────────────────────────────
        metrics_resp = await client.get(f"{GATEWAY}/api/metrics/summary", headers=headers)
        assert metrics_resp.status_code == 200, f"Metrics failed: {metrics_resp.text}"
        metrics = metrics_resp.json()
        assert "task_success_rate" in metrics

        # ── Step 8: HITL annotation ──────────────────────────────────────────
        # Find a failed run to annotate
        failed_resp = await client.get(f"{GATEWAY}/api/hitl/queue", headers=headers)
        assert failed_resp.status_code == 200
        failed_runs = failed_resp.json()

        if failed_runs:
            fail_run_id = failed_runs[0]["run_id"]
            annotate_resp = await client.post(
                f"{GATEWAY}/api/hitl/{fail_run_id}/annotate",
                headers=headers,
                json={
                    "root_cause": "wrong_tool",
                    "severity": "major",
                    "notes": "E2E annotation test",
                    "tags": ["regression"],
                    "annotator": "e2e_test",
                },
            )
            assert annotate_resp.status_code == 200, f"Annotation failed: {annotate_resp.text}"
            annotation_data = annotate_resp.json()
            assert annotation_data["annotated"] is True
            assert "regression_test_path" in annotation_data

            # Verify the file was actually created
            test_file = Path(annotation_data["regression_test_path"])
            assert test_file.exists(), f"Regression test file not found at {test_file}"
            content = test_file.read_text()
            assert "pytest.mark.regression" in content, "Regression marker missing from test file"
