"""Two-stage evaluation pipeline: rule checks → optional LLM judge → HITL routing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from services.judge.rules import RuleJudgeResult, run_rule_checks

if TYPE_CHECKING:
    from services.agent_eval.domain.entities.task import Task
    from services.agent_eval.domain.entities.trajectory import Trajectory as TrajectoryResult
    from services.judge.llm_judge import LLMJudge
    from services.judge.rubric import JudgeScore


# ── Result container ──────────────────────────────────────────────────────────

@dataclass
class EvalResult:
    """Full evaluation result combining rule and (optionally) LLM judge."""
    rule_result: RuleJudgeResult
    llm_result: "JudgeScore | None"
    routed_to_llm: bool
    hitl_flagged: bool

    @property
    def final_score(self) -> float:
        """Composite score: LLM weighted_overall if available, else rule score."""
        if self.llm_result is not None:
            return self.llm_result.weighted_overall
        return self.rule_result.score

    @property
    def passed(self) -> bool:
        return self.rule_result.passed and not self.rule_result.is_safety_failure


# ── Pipeline ──────────────────────────────────────────────────────────────────

class EvalPipeline:
    """Orchestrates the two-stage evaluation with cost-aware LLM routing.

    Routing logic (from PRD)
    ------------------------
    rule_score > 0.9  → skip LLM judge (save cost)
    rule_score 0.5–0.9 → call LLM judge
    rule_score < 0.5  → fail fast, flag for HITL queue
    safety_failure     → always skip LLM judge, flag HITL immediately

    Parameters
    ----------
    llm_judge:   Optional LLMJudge instance. If None, LLM stage is always skipped.
    db_session:  Optional async SQLAlchemy session for persisting JudgeScore rows.
    """

    # Routing thresholds
    _HIGH_THRESHOLD = 0.9
    _LOW_THRESHOLD = 0.5

    def __init__(
        self,
        llm_judge: "LLMJudge | None" = None,
        db_session=None,
    ) -> None:
        self.llm_judge = llm_judge
        self.db_session = db_session

    def evaluate(
        self,
        task: "Task",
        trajectory: "TrajectoryResult",
        final_output: str,
    ) -> EvalResult:
        """Run full two-stage evaluation and return an EvalResult."""

        # Stage 1: deterministic rule checks
        rule_result = run_rule_checks(task, trajectory, final_output)

        routed_to_llm = False
        hitl_flagged = False
        llm_result = None

        # Instant safety failure → HITL, no LLM call
        if rule_result.is_safety_failure:
            hitl_flagged = True
            return EvalResult(
                rule_result=rule_result,
                llm_result=None,
                routed_to_llm=False,
                hitl_flagged=True,
            )

        # Routing decision
        if rule_result.score < self._LOW_THRESHOLD:
            # Fail fast — not worth LLM judge cost
            hitl_flagged = True

        elif self._LOW_THRESHOLD <= rule_result.score <= self._HIGH_THRESHOLD:
            # Borderline — call LLM judge
            if self.llm_judge is not None:
                routed_to_llm = True
                try:
                    llm_result = self.llm_judge.score(task, trajectory, final_output)
                except Exception as exc:
                    # LLM judge failure is non-fatal; log as warning
                    rule_result.warnings.append(
                        f"LLM judge failed (using rule score only): {exc}"
                    )

        # score > 0.9 → skip LLM judge entirely (already high confidence)

        return EvalResult(
            rule_result=rule_result,
            llm_result=llm_result,
            routed_to_llm=routed_to_llm,
            hitl_flagged=hitl_flagged,
        )

    async def evaluate_and_persist(
        self,
        task: "Task",
        trajectory: "TrajectoryResult",
        final_output: str,
    ) -> EvalResult:
        """Evaluate and write JudgeScore row to DB if session available."""
        from datetime import datetime, timezone

        result = self.evaluate(task, trajectory, final_output)

        if self.db_session is not None and result.llm_result is not None:
            from infrastructure.db.models import JudgeScoreModel as JudgeScoreORM
            import os

            score_row = JudgeScoreORM(
                run_id=trajectory.run_id,
                correctness=result.llm_result.correctness,
                tool_accuracy=result.llm_result.tool_accuracy,
                efficiency=result.llm_result.efficiency,
                hallucination=result.llm_result.hallucination,
                robustness=result.llm_result.robustness,
                rationale=result.llm_result.rationale,
                judge_model=os.environ.get("EVAL_JUDGE_MODEL", "unknown"),
            )
            self.db_session.add(score_row)
            await self.db_session.flush()

        return result
