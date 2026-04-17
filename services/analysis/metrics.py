"""Per-run and per-suite metric computation."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.runner import SuiteResult, TaskRunResult

# Token cost per 1M tokens (Haiku input/output blended estimate)
_COST_PER_TOKEN_USD = 0.000_001_25  # $1.25 / 1M tokens (Haiku blended)


def compute_run_metrics(run_result: "TaskRunResult") -> dict:
    """Compute per-run metric dict from a TaskRunResult."""
    traj = run_result.trajectory
    return {
        "run_id": run_result.run_id,
        "task_id": run_result.task.id,
        "task_name": run_result.task.name,
        "category": run_result.task.category,
        "status": run_result.status,
        "passed": run_result.status == "completed",
        "latency_ms": run_result.duration_ms,
        "token_total": traj.token_total if traj else 0,
        "step_count": traj.step_count if traj else 0,
        "step_efficiency_ratio": traj.step_efficiency_ratio if traj else 0.0,
        "error_count": traj.error_count if traj else 0,
        "cost_usd": round(
            (traj.token_total if traj else 0) * _COST_PER_TOKEN_USD, 6
        ),
        "tool_names_called": traj.tool_names_called if traj else [],
        "exit_reason": run_result.exit_reason,
    }


def compute_suite_metrics(
    suite_result: "SuiteResult",
    prev_metrics: dict | None = None,
) -> dict:
    """Compute aggregate metrics across all runs in a suite.

    Parameters
    ----------
    suite_result:  The completed SuiteResult.
    prev_metrics:  Metrics dict from the previous run (for regression_delta).
    """
    run_metrics = [compute_run_metrics(r) for r in suite_result.runs]

    total = len(run_metrics)
    if total == 0:
        return {}

    passed = [m for m in run_metrics if m["passed"]]
    task_success_rate = len(passed) / total

    # Latency percentiles
    latencies = sorted(m["latency_ms"] for m in run_metrics)
    p50_idx = int(0.50 * len(latencies))
    p99_idx = min(int(0.99 * len(latencies)), len(latencies) - 1)
    p50_latency_ms = latencies[p50_idx]
    p99_latency_ms = latencies[p99_idx]

    # Tool error rate
    total_steps = sum(m["step_count"] for m in run_metrics)
    total_errors = sum(m["error_count"] for m in run_metrics)
    tool_error_rate = total_errors / total_steps if total_steps > 0 else 0.0

    # Cost
    avg_cost_usd = sum(m["cost_usd"] for m in run_metrics) / total

    # Safety pass rate (adversarial tasks only)
    adversarial = [m for m in run_metrics if m["category"] == "adversarial"]
    safety_pass_rate: float | None = None
    if adversarial:
        safety_pass_rate = sum(1 for m in adversarial if m["passed"]) / len(adversarial)

    # Regression delta vs previous run
    regression_delta: float | None = None
    regression_detected = False
    if prev_metrics and "task_success_rate" in prev_metrics:
        regression_delta = task_success_rate - prev_metrics["task_success_rate"]
        regression_detected = regression_delta < -0.05  # >5% drop

    # Average score per dimension (from run_metrics if llm scores attached)
    dimension_scores: dict[str, list[float]] = {
        "correctness": [], "tool_accuracy": [],
        "efficiency": [], "hallucination": [], "robustness": [],
    }
    for m in run_metrics:
        for dim in dimension_scores:
            if dim in m:
                dimension_scores[dim].append(m[dim])
    avg_score_per_dimension = {
        dim: round(sum(vals) / len(vals), 4) if vals else None
        for dim, vals in dimension_scores.items()
    }

    return {
        "total_runs": total,
        "pass_count": len(passed),
        "fail_count": total - len(passed),
        "task_success_rate": round(task_success_rate, 4),
        "p50_latency_ms": p50_latency_ms,
        "p99_latency_ms": p99_latency_ms,
        "tool_error_rate": round(tool_error_rate, 4),
        "avg_cost_usd": round(avg_cost_usd, 6),
        "total_cost_usd": round(sum(m["cost_usd"] for m in run_metrics), 6),
        "safety_pass_rate": safety_pass_rate,
        "regression_delta": regression_delta,
        "regression_detected": regression_detected,
        "avg_score_per_dimension": avg_score_per_dimension,
        "per_run": run_metrics,
    }
