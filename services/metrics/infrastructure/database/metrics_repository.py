"""MetricsRepository: computes and retrieves SuiteMetrics from the database."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from services.metrics.domain.entities.metrics import SuiteMetrics
from infrastructure.db.models import (
    EvalRunModel,
    JudgeScoreModel,
    TrajectoryModel,
)


class MetricsRepository:
    """Read-only analytics repository.  Runs raw/ORM queries against the
    shared PostgreSQL database to compute SuiteMetrics aggregates."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def compute_suite_metrics(self, run_ids: list[str]) -> SuiteMetrics:
        """Compute SuiteMetrics for *run_ids*.

        If *run_ids* is empty, aggregates across all completed runs.
        """
        run_filter = (
            EvalRunModel.run_id.in_(run_ids) if run_ids else EvalRunModel.status.in_(["PASS", "FAIL", "ERROR"])
        )

        # ── pass / fail counts ──────────────────────────────────────────
        count_stmt = select(
            func.count(EvalRunModel.run_id).label("total"),
            func.sum(
                func.cast(EvalRunModel.status == "PASS", type_=func.Integer if False else None)
            ).label("passed"),
        ).where(run_filter)

        # Use a simpler approach that works across DB engines
        all_runs_stmt = select(EvalRunModel).where(run_filter)
        all_runs_result = await self._session.execute(all_runs_stmt)
        all_runs: Sequence[EvalRunModel] = all_runs_result.scalars().all()

        total = len(all_runs)
        passed = sum(1 for r in all_runs if r.status == "PASS")
        task_success_rate = passed / max(1, total)

        # ── latency (from eval_runs.started_at / ended_at) ─────────────
        durations_ms = []
        for run in all_runs:
            if run.started_at and run.ended_at:
                ms = int((run.ended_at - run.started_at).total_seconds() * 1000)
                durations_ms.append(ms)
        durations_ms.sort()
        latency_p50, latency_p99 = self._percentiles(durations_ms, [50, 99])

        # ── token + cost from trajectories ──────────────────────────────
        run_ids_list = [r.run_id for r in all_runs]
        traj_stmt = select(TrajectoryModel).where(TrajectoryModel.run_id.in_(run_ids_list))
        traj_result = await self._session.execute(traj_stmt)
        trajs: Sequence[TrajectoryModel] = traj_result.scalars().all()

        all_tokens = []
        tool_errors = 0
        total_steps = 0
        for traj in trajs:
            spans = traj.spans or []
            tokens = sum(s.get("attributes", {}).get("tokens_total", 0) for s in spans)
            all_tokens.append(tokens)
            tool_errors += sum(1 for s in spans if s.get("error") and "TOOL" in s.get("span_type", ""))
            total_steps += len([s for s in spans if s.get("span_type") in ("LLM_CALL", "TOOL_CALL")])

        avg_tokens = sum(all_tokens) / max(1, len(all_tokens))
        # Cost estimate: claude-haiku ~$0.25/M input + $1.25/M output (simplified)
        cost_per_token = 0.00000125
        estimated_cost = avg_tokens * cost_per_token * max(1, len(all_tokens))
        tool_error_rate = tool_errors / max(1, total_steps)

        # ── judge scores ────────────────────────────────────────────────
        score_stmt = select(JudgeScoreModel).where(JudgeScoreModel.run_id.in_(run_ids_list))
        score_result = await self._session.execute(score_stmt)
        scores: Sequence[JudgeScoreModel] = score_result.scalars().all()
        score_values = [s.score_value for s in scores]
        avg_correctness = sum(score_values) / max(1, len(score_values))

        return SuiteMetrics(
            task_success_rate=task_success_rate,
            latency_p50_ms=latency_p50,
            latency_p99_ms=latency_p99,
            avg_tokens_per_task=avg_tokens,
            estimated_cost_usd=estimated_cost,
            tool_error_rate=tool_error_rate,
            avg_step_efficiency=total_steps / max(1, total),
            error_count=total - passed,
            avg_correctness=avg_correctness,
            hallucination_rate=0.0,       # Populated when judge uploads dimension data
            safety_pass_rate=1.0,
            regression_detected=False,
            regression_delta=None,
            regressed_tasks=[],
            improved_tasks=[],
            run_timestamp=datetime.now(timezone.utc),
            run_id=run_ids_list[0] if run_ids_list else "aggregate",
        )

    async def get_history(self, days: int = 7) -> list[SuiteMetrics]:
        """Return one SuiteMetrics aggregate per day for the last *days* days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(EvalRunModel)
            .where(EvalRunModel.started_at >= cutoff)
            .order_by(EvalRunModel.started_at.asc())
        )
        result = await self._session.execute(stmt)
        runs: Sequence[EvalRunModel] = result.scalars().all()

        # Group by date
        by_date: dict[str, list[EvalRunModel]] = {}
        for run in runs:
            day = run.started_at.strftime("%Y-%m-%d") if run.started_at else "unknown"
            by_date.setdefault(day, []).append(run)

        history = []
        for _day, day_runs in by_date.items():
            run_ids = [r.run_id for r in day_runs]
            metrics = await self.compute_suite_metrics(run_ids)
            history.append(metrics)

        return history

    async def detect_regression(
        self, current: SuiteMetrics, prev: SuiteMetrics
    ) -> bool:
        """Return True if success rate dropped by more than 10 percentage points."""
        if prev.task_success_rate == 0.0:
            return False
        delta = current.task_success_rate - prev.task_success_rate
        return delta < -0.10

    async def get_active_alerts(self) -> list[dict]:
        """Return alert conditions based on the latest SuiteMetrics."""
        from services.metrics.infrastructure.alerting.alert_engine import AlertEngine
        metrics = await self.compute_suite_metrics([])
        engine = AlertEngine()
        alerts = engine.check(metrics)
        return [
            {
                "metric_name": a.metric_name,
                "severity": a.severity,
                "message": a.message,
                "actual_value": a.actual_value,
                "threshold": a.threshold,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _percentiles(sorted_values: list[float], percentiles: list[int]) -> tuple[float, ...]:
        if not sorted_values:
            return tuple(0.0 for _ in percentiles)
        results = []
        n = len(sorted_values)
        for p in percentiles:
            idx = max(0, int(n * p / 100) - 1)
            results.append(sorted_values[min(idx, n - 1)])
        return tuple(results)

