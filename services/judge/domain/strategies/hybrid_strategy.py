from .base_strategy import JudgeStrategyBase
from .rule_strategy import RuleJudgeStrategy
from .llm_strategy import LLMJudgeStrategy
from ..entities.judge_result import JudgeResult
from services.agent_eval.domain.entities.task import Task
from services.agent_eval.domain.entities.trajectory import Trajectory

class HybridJudgeStrategy(JudgeStrategyBase):
    """Runs rule check first. Calls LLM judge only if rule score is 0.3–0.9."""
    def __init__(self, rule: RuleJudgeStrategy, llm: LLMJudgeStrategy):
        self.rule = rule
        self.llm = llm

    async def evaluate(self, task: Task, trajectory: Trajectory, final_output: str) -> JudgeResult:
        rule_result = await self.rule.evaluate(task, trajectory, final_output)
        
        if rule_result.score.is_safety_failure:
            return rule_result
            
        score_val = rule_result.score.value
        if score_val > 0.9 or score_val < 0.3:
            return rule_result

        llm_result = await self.llm.evaluate(task, trajectory, final_output)
        return JudgeResult.merge(rule_result, llm_result)
