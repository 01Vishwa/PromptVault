"""SuiteMetrics domain entity — all performance and quality dimensions."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SuiteMetrics:
    """Single point-in-time snapshot of the agent evaluation system."""

    # Pass/fail
    task_success_rate: float                   # 0.0 – 1.0
    error_count: int

    # Latency
    latency_p50_ms: float
    latency_p99_ms: float

    # Token / cost
    avg_tokens_per_task: float
    estimated_cost_usd: float

    # Tool utilisation
    tool_error_rate: float
    avg_step_efficiency: float

    # LLM judge dimensions (0.0 – 1.0)
    avg_correctness: float
    hallucination_rate: float
    safety_pass_rate: float

    # Regression detection
    regression_detected: bool
    regression_delta: Optional[float]          # None if no previous run to compare to
    regressed_tasks: list[str] = field(default_factory=list)
    improved_tasks: list[str] = field(default_factory=list)

    # Metadata
    run_timestamp: datetime = field(default_factory=datetime.utcnow)
    run_id: str = "aggregate"
