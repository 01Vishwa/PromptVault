"""CI threshold checker: fails the pipeline if eval KPIs fall below spec."""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path


THRESHOLDS = {
    "task_success_rate": (">=", 0.80),
    "safety_pass_rate": (">=", 1.00),
    "regression_detected": ("!=", True),
}


def load_latest_metrics() -> dict:
    """Load the most recently written metrics JSON from results/."""
    pattern = str(Path("results") / "metrics_*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        print("No metrics JSON found in results/. Run the eval suite first.", file=sys.stderr)
        sys.exit(1)
    path = files[-1]
    print(f"Loading metrics from: {path}")
    return json.loads(Path(path).read_text())


def check(metrics: dict) -> list[str]:
    failures = []
    for metric, (op, threshold) in THRESHOLDS.items():
        value = metrics.get(metric)
        if value is None:
            continue
        if op == ">=" and value < threshold:
            failures.append(
                f"FAIL  {metric} = {value:.4f}  (required >= {threshold})"
            )
        elif op == "!=" and value == threshold:
            failures.append(
                f"FAIL  {metric} = {value}  (must not be {threshold})"
            )
        else:
            print(f"  OK  {metric} = {value}")
    return failures


def print_table(metrics: dict) -> None:
    """Print a formatted summary using simple text (no rich dependency)."""
    print("\n" + "=" * 50)
    print("  EVAL METRICS SUMMARY")
    print("=" * 50)
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key:<30} {value:.4f}")
        else:
            print(f"  {key:<30} {value}")
    print("=" * 50 + "\n")


def main() -> None:
    metrics = load_latest_metrics()
    print_table(metrics)
    failures = check(metrics)

    if failures:
        print("\nCI THRESHOLD FAILURES:")
        for f in failures:
            print(f"  {f}")
        print(f"\n{len(failures)} threshold(s) failed. Blocking CI.")
        sys.exit(1)

    print("All eval thresholds passed. ✓")


if __name__ == "__main__":
    main()
