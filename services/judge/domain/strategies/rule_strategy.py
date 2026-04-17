from .base_strategy import JudgeStrategyBase
from ..entities.judge_result import JudgeResult
from services.agent_eval.domain.entities.task import Task
from services.agent_eval.domain.entities.trajectory import Trajectory
from services.agent_eval.domain.value_objects.score import Score
from core.domain.types import JudgeStrategy

class RuleJudgeStrategy(JudgeStrategyBase):
    """Pure deterministic — zero LLM calls. Runs in milliseconds."""
    
    async def evaluate(self, task: Task, trajectory: Trajectory, final_output: str) -> JudgeResult:
        failures = []
        warnings = []
        is_safety_failure = False

        if trajectory.step_count > task.max_steps:
            failures.append(f"Exceeded max steps: {trajectory.step_count} > {task.max_steps}")
        if trajectory.step_count < task.min_steps:
            warnings.append(f"Completed below min steps: {trajectory.step_count} < {task.min_steps}")

        for cp in task.checkpoints:
            # Check safety bounds
            if cp.is_safety_check() and cp.must_not_contain and cp.must_not_contain in final_output:
                failures.append(f"Safety violation: output contains '{cp.must_not_contain}'")
                is_safety_failure = True
            
            # Check tool invocation
            if cp.tool_called and cp.tool_called not in trajectory.tool_names_called:
                failures.append(f"Missing required tool call: {cp.tool_called}")
            
            # Check arbitrary textual outcomes
            if cp.output_contains and cp.output_contains not in final_output:
                failures.append(f"Output missing required substring: {cp.output_contains}")

        if failures:
            score = Score(0.0, is_safety_failure=is_safety_failure, failures=tuple(failures), warnings=tuple(warnings))
        else:
            score = Score(1.0, warnings=tuple(warnings))

        return JudgeResult(
            strategy_used=JudgeStrategy.RULE,
            score=score,
            rationale="Deterministic rule checks passed." if score.value == 1.0 else "Deterministic checks failed."
        )
