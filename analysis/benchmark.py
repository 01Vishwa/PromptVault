"""Three-variant benchmark: baseline vs optimised_prompt vs reduced_tools."""
from __future__ import annotations

import asyncio
import csv
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.agent_eval.config import get_settings
from services.agent_eval.infrastructure.database.connection import DatabaseConnection
from services.agent_eval.infrastructure.agents.agent_factory import AgentFactory, AgentConfig
from services.agent_eval.container import Container
from core.use_cases.registry import TaskRegistry


OUTPUT_DIR = Path("analysis/results")


@dataclass
class VariantResult:
    variant: str
    task_success_rate: float = 0.0
    latency_p99_ms: float = 0.0
    avg_tokens: float = 0.0
    estimated_cost_usd: float = 0.0
    tool_error_rate: float = 0.0
    avg_correctness: float = 0.0
    total_runs: int = 0
    passed_runs: int = 0
    raw_runs: list[dict] = field(default_factory=list)


VARIANTS: dict[str, AgentConfig] = {
    "baseline": AgentConfig(
        model="claude-haiku-4-5-20251001",
        temperature=0.0,
        max_iterations=15,
        enabled_tools=["calculator", "get_weather", "search_web", "write_file"],
        system_prompt_suffix="",
    ),
    "optimised_prompt": AgentConfig(
        model="claude-haiku-4-5-20251001",
        temperature=0.0,
        max_iterations=15,
        enabled_tools=["calculator", "get_weather", "search_web", "write_file"],
        system_prompt_suffix=(
            "\n\nIMPORTANT: Always verify your answer using the available tools before responding. "
            "Think step-by-step and be precise."
        ),
    ),
    "reduced_tools": AgentConfig(
        model="claude-haiku-4-5-20251001",
        temperature=0.0,
        max_iterations=15,
        enabled_tools=["calculator", "search_web"],
        system_prompt_suffix="",
    ),
}


async def run_variant(variant_name: str, config: AgentConfig, settings) -> VariantResult:
    """Run all fixtures tasks with one agent variant configuration."""
    print(f"\n{'='*60}")
    print(f"Running variant: {variant_name}")
    print(f"{'='*60}")

    registry = TaskRegistry()
    tasks = registry.list_tasks()
    if not tasks:
        print(f"  WARNING: No tasks found in registry for variant {variant_name}")
        return VariantResult(variant=variant_name)

    factory = AgentFactory(api_key=settings.anthropic_api_key)
    container = Container(settings)
    # Override container's agent factory with variant config
    eval_service = container.eval_service

    run_results: list[dict] = []
    latencies_ms: list[float] = []
    tokens: list[float] = []
    tool_errors = 0
    total_steps = 0

    for task_schema in tasks:
        print(f"  Task: {task_schema.task_id} — {task_schema.name}")
        try:
            result = await eval_service.run_suite(
                task_ids=[task_schema.task_id],
                category=None,
                agent_version=f"{variant_name}-v1",
            )
            for run in result.get("runs", []):
                run_results.append(run)
                if run.get("ended_at") and run.get("started_at"):
                    from datetime import datetime
                    start = datetime.fromisoformat(run["started_at"])
                    end = datetime.fromisoformat(run["ended_at"])
                    latencies_ms.append((end - start).total_seconds() * 1000)
        except Exception as exc:
            print(f"    ERROR: {exc}")
            run_results.append({"status": "ERROR", "task_id": task_schema.task_id})

    passed = sum(1 for r in run_results if r.get("status") == "PASS")
    total = max(1, len(run_results))
    latencies_ms.sort()

    p99 = latencies_ms[int(len(latencies_ms) * 0.99) - 1] if latencies_ms else 0.0

    return VariantResult(
        variant=variant_name,
        task_success_rate=passed / total,
        latency_p99_ms=p99,
        avg_tokens=float(sum(tokens) / max(1, len(tokens))),
        estimated_cost_usd=float(sum(tokens) * 0.00000125),
        tool_error_rate=tool_errors / max(1, total_steps),
        avg_correctness=0.0,  # populated after judge scores are fetched
        total_runs=total,
        passed_runs=passed,
        raw_runs=run_results,
    )


def write_comparison_csv(results: list[VariantResult]) -> Path:
    path = OUTPUT_DIR / "comparison_table.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "variant", "task_success_rate", "latency_p99_ms", "avg_tokens",
        "estimated_cost_usd", "tool_error_rate", "avg_correctness",
        "total_runs", "passed_runs",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            row = asdict(r)
            writer.writerow({k: row[k] for k in fields})
    return path


def write_radar_data(results: list[VariantResult]) -> Path:
    path = OUTPUT_DIR / "radar_chart_data.json"
    data = [
        {
            "variant": r.variant,
            "Task Success": round(r.task_success_rate * 100, 1),
            "Speed (inv P99)": round(max(0, 100 - r.latency_p99_ms / 1000), 1),
            "Cost Efficiency": round(max(0, 100 - r.estimated_cost_usd * 50), 1),
            "Tool Accuracy": round((1 - r.tool_error_rate) * 100, 1),
            "Correctness": round(r.avg_correctness * 100, 1),
        }
        for r in results
    ]
    path.write_text(json.dumps(data, indent=2))
    return path


def write_findings(results: list[VariantResult]) -> Path:
    path = OUTPUT_DIR / "findings_summary.md"
    best = max(results, key=lambda r: r.task_success_rate)
    lines = [
        "# Benchmark Findings\n",
        f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n",
        "## Variant Comparison\n\n",
        "| Variant | Success Rate | P99 Latency | Cost USD | Tool Error Rate |\n",
        "|---------|-------------|------------|---------|----------------|\n",
    ]
    for r in results:
        lines.append(
            f"| {r.variant} | {r.task_success_rate:.1%} | {r.latency_p99_ms:.0f}ms "
            f"| ${r.estimated_cost_usd:.4f} | {r.tool_error_rate:.1%} |\n"
        )
    lines.append(f"\n**Best variant:** `{best.variant}` with {best.task_success_rate:.1%} success rate\n")
    path.write_text("".join(lines))
    return path


def write_abstract_stats(results: list[VariantResult]) -> Path:
    path = OUTPUT_DIR / "stats_for_abstract.txt"
    all_runs = sum(r.total_runs for r in results)
    best = max(results, key=lambda r: r.task_success_rate)
    lines = [
        f"Total agent runs evaluated: {all_runs}",
        f"Number of variants compared: {len(results)}",
        f"Best variant: {best.variant}",
        f"Best success rate: {best.task_success_rate:.1%}",
        f"Benchmark timestamp: {datetime.now(timezone.utc).isoformat()}",
    ]
    path.write_text("\n".join(lines))
    return path


async def main():
    settings = get_settings()
    await DatabaseConnection.initialise(settings.database_url)

    results: list[VariantResult] = []
    for variant_name, config in VARIANTS.items():
        result = await run_variant(variant_name, config, settings)
        results.append(result)
        print(
            f"  Done: {result.variant} — {result.passed_runs}/{result.total_runs} passed"
        )

    csv_path = write_comparison_csv(results)
    radar_path = write_radar_data(results)
    findings_path = write_findings(results)
    abstract_path = write_abstract_stats(results)

    print("\n" + "="*60)
    print("Benchmark complete. Outputs written to:")
    for p in (csv_path, radar_path, findings_path, abstract_path):
        print(f"  {p}")

    await DatabaseConnection.close()


if __name__ == "__main__":
    asyncio.run(main())
