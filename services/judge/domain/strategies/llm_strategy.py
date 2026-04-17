import json
from .base_strategy import JudgeStrategyBase
from ..entities.judge_result import JudgeResult
from services.agent_eval.domain.entities.task import Task
from services.agent_eval.domain.entities.trajectory import Trajectory
from services.agent_eval.domain.value_objects.score import Score
from core.domain.types import JudgeStrategy
from ...infrastructure.llm.anthropic_client import AnthropicClient, BudgetTracker
from core.errors.exceptions import JudgeBudgetExceededError

class LLMJudgeStrategy(JudgeStrategyBase):
    def __init__(self, client: AnthropicClient, model: str, budget_tracker: BudgetTracker):
        self.client = client
        self.model = model
        self.budget_tracker = budget_tracker

    async def evaluate(self, task: Task, trajectory: Trajectory, final_output: str) -> JudgeResult:
        if not self.budget_tracker.can_afford(1000):
            raise JudgeBudgetExceededError("Insufficient budget for LLM evaluation.")

        system_prompt = "You are an expert AI behavior evaluator. Output strictly JSON adhering to the evaluation dimensions."
        
        user_prompt = f"""
        Task: {task.prompt}
        Expected Outcome: {task.expected_outcome}
        
        Agent Trajectory:
        Final Output: {final_output}
        Tools Used: {trajectory.tool_names_called}
        Total Steps: {trajectory.step_count}
        
        Evaluate the agent on:
        - correctness (0-100)
        - tool_accuracy (0-100)
        - efficiency (0-100)
        - hallucination (0-100)
        - robustness (0-100)
        
        Return JSON format: {{"correctness": 90, "tool_accuracy": 100, "efficiency": 80, "hallucination": 0, "robustness": 90, "rationale": "..."}}
        """

        try:
            response, in_tokens, out_tokens = await self.client.complete(system_prompt, user_prompt, max_tokens=1000)
            self.budget_tracker.record(in_tokens, out_tokens)
            
            data = json.loads(response)
            
            avg_score = (data.get("correctness", 0) + data.get("tool_accuracy", 0) + data.get("efficiency", 0) + data.get("robustness", 0) - data.get("hallucination", 0)) / 400.0
            score_val = max(0.0, min(1.0, avg_score))

            return JudgeResult(
                strategy_used=JudgeStrategy.LLM,
                score=Score(score_val),
                rationale=data.get("rationale", "No rationale provided."),
                correctness=data.get("correctness"),
                tool_accuracy=data.get("tool_accuracy"),
                efficiency=data.get("efficiency"),
                hallucination=data.get("hallucination"),
                robustness=data.get("robustness"),
                cost_usd=self.budget_tracker.total_spent
            )
        except Exception as e:
            return JudgeResult(
                strategy_used=JudgeStrategy.LLM,
                score=Score(0.0, failures=(f"LLM Evaluation Error: {str(e)}",)),
                rationale="Evaluation failed due to LLM error."
            )
