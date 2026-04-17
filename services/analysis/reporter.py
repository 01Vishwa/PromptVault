"""Writes eval run results and metric summaries to the results/ directory."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.runner import SuiteResult

_RESULTS_DIR = Path("results")


def _latest_metrics_file(results_dir: Path = _RESULTS_DIR) -> Path | None:
    """Return the most recently written metrics_*.json file, or None."""
    files = sorted(results_dir.glob("metrics_*.json"), reverse=True)
    return files[0] if files else None


def load_prev_metrics(results_dir: Path = _RESULTS_DIR) -> dict | None:
    """Load the most recent metrics JSON for regression delta comparison."""
    path = _latest_metrics_file(results_dir)
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_run_json(
    suite_result: "SuiteResult",
    metrics: dict,
    output_dir: str | Path = "results",
) -> Path:
    """Write full run detail JSON and a metrics summary JSON.

    Files written
    -------------
    results/run_YYYYMMDD_HHMMSS.json    ← full detail (trajectories + scores)
    results/metrics_YYYYMMDD_HHMMSS.json ← summary only (for CI gate)

    Returns the path to the full run JSON.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # ── Full run detail ───────────────────────────────────────────────────────
    run_detail = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pass_count": suite_result.pass_count,
        "fail_count": suite_result.fail_count,
        "error_count": suite_result.error_count,
        "total_duration_ms": suite_result.total_duration_ms,
        "pass_rate": suite_result.pass_rate,
        "runs": [
            {
                "run_id": r.run_id,
                "task_id": r.task.id,
                "task_name": r.task.name,
                "category": r.task.category,
                "status": r.status,
                "duration_ms": r.duration_ms,
                "exit_reason": r.exit_reason,
                "trajectory": r.trajectory.model_dump() if r.trajectory else None,
            }
            for r in suite_result.runs
        ],
        "metrics": metrics,
    }

    run_path = out / f"run_{ts}.json"
    run_path.write_text(json.dumps(run_detail, indent=2, default=str), encoding="utf-8")

    # ── Metrics summary only ──────────────────────────────────────────────────
    metrics_slim = {k: v for k, v in metrics.items() if k != "per_run"}
    metrics_slim["generated_at"] = datetime.now(timezone.utc).isoformat()
    metrics_path = out / f"metrics_{ts}.json"
    metrics_path.write_text(json.dumps(metrics_slim, indent=2, default=str), encoding="utf-8")

    return run_path
