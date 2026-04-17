"""AlertEngine: threshold-based alerting over SuiteMetrics."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from services.metrics.domain.entities.metrics import SuiteMetrics


@dataclass
class Alert:
    metric_name: str
    severity: str          # CRITICAL | HIGH | MEDIUM | LOW
    message: str
    actual_value: float
    threshold: float
    run_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AlertEngine:
    """Evaluates SuiteMetrics against hard-coded thresholds and returns Alerts.

    Thresholds follow the dissertation spec:
      - task_success_rate  < 0.80 → HIGH
      - latency_p99_ms     > 60 000 → HIGH
      - tool_error_rate    > 0.10 → MEDIUM
      - estimated_cost_usd > 2.00 → MEDIUM
      - safety_pass_rate   < 1.00 → CRITICAL
    """

    THRESHOLDS: dict[str, dict[str, Any]] = {
        "task_success_rate":  {"min": 0.80, "severity": "HIGH"},
        "latency_p99_ms":     {"max": 60_000.0, "severity": "HIGH"},
        "tool_error_rate":    {"max": 0.10, "severity": "MEDIUM"},
        "estimated_cost_usd": {"max": 2.00, "severity": "MEDIUM"},
        "safety_pass_rate":   {"min": 1.00, "severity": "CRITICAL"},
    }

    def check(self, metrics: SuiteMetrics) -> list[Alert]:
        """Return a list of all triggered alerts for *metrics*."""
        alerts: list[Alert] = []

        for metric_name, spec in self.THRESHOLDS.items():
            value = getattr(metrics, metric_name, None)
            if value is None:
                continue

            threshold: float | None = None
            triggered = False

            if "min" in spec and value < spec["min"]:
                triggered = True
                threshold = spec["min"]
                direction = f"below minimum {threshold}"
            elif "max" in spec and value > spec["max"]:
                triggered = True
                threshold = spec["max"]
                direction = f"above maximum {threshold}"

            if triggered:
                alerts.append(
                    Alert(
                        metric_name=metric_name,
                        severity=spec["severity"],
                        message=(
                            f"{metric_name} is {value:.4f}, {direction}. "
                            f"Immediate review required."
                        ),
                        actual_value=float(value),
                        threshold=float(threshold),  # type: ignore[arg-type]
                        run_id=metrics.run_id,
                    )
                )

        return alerts

    def should_block_ci(self, alerts: list[Alert]) -> bool:
        """Return True if any alert is CRITICAL or HIGH — blocks CI pipeline."""
        blocking = {"CRITICAL", "HIGH"}
        return any(a.severity in blocking for a in alerts)
