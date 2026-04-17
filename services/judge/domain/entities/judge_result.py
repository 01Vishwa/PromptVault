from dataclasses import dataclass
from typing import Optional
from core.domain.types import JudgeStrategy
from services.agent_eval.domain.value_objects.score import Score

@dataclass
class JudgeResult:
    strategy_used: JudgeStrategy
    score: Score
    rationale: str
    correctness: Optional[int] = None
    tool_accuracy: Optional[int] = None
    efficiency: Optional[int] = None
    hallucination: Optional[int] = None
    robustness: Optional[int] = None
    cost_usd: float = 0.0
    cached: bool = False

    @classmethod
    def merge(cls, rule_result: 'JudgeResult', llm_result: 'JudgeResult') -> 'JudgeResult':
        return cls(
            strategy_used=JudgeStrategy.HYBRID,
            score=rule_result.score + llm_result.score,
            rationale=f"RULE: {rule_result.rationale}\nLLM: {llm_result.rationale}",
            correctness=llm_result.correctness,
            tool_accuracy=llm_result.tool_accuracy,
            efficiency=llm_result.efficiency,
            hallucination=llm_result.hallucination,
            robustness=llm_result.robustness,
            cost_usd=llm_result.cost_usd,
            cached=llm_result.cached
        )
