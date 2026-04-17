from ...domain.entities.judge_result import JudgeResult
from ...domain.strategies.base_strategy import JudgeStrategyBase
from ...domain.strategies.rule_strategy import RuleJudgeStrategy
from ...domain.strategies.llm_strategy import LLMJudgeStrategy
from ...domain.strategies.hybrid_strategy import HybridJudgeStrategy
from ...infrastructure.llm.cache import JudgeCache
from services.agent_eval.domain.entities.task import Task
from services.agent_eval.domain.entities.trajectory import Trajectory

class StrategyFactory:
    @staticmethod
    def create(strategy_name: str, rule: RuleJudgeStrategy, llm: LLMJudgeStrategy, hybrid: HybridJudgeStrategy) -> JudgeStrategyBase:
        if strategy_name == "rule":
            return rule
        elif strategy_name == "llm":
            return llm
        return hybrid

class JudgeService:
    def __init__(self, rule_strategy: RuleJudgeStrategy, llm_strategy: LLMJudgeStrategy, 
                 hybrid_strategy: HybridJudgeStrategy, cache: JudgeCache):
        self.rule_strategy = rule_strategy
        self.llm_strategy = llm_strategy
        self.hybrid_strategy = hybrid_strategy
        self.cache = cache

    async def evaluate(self, task: Task, trajectory: Trajectory, output: str, strategy: str) -> JudgeResult:
        cached = self.cache.get(task.task_id, trajectory.trajectory_hash)
        if cached:
            return cached

        strat = StrategyFactory.create(strategy, self.rule_strategy, self.llm_strategy, self.hybrid_strategy)
        result = await strat.evaluate(task, trajectory, output)
        
        self.cache.set(task.task_id, trajectory.trajectory_hash, result)
        return result

    async def pairwise(self, task: Task, traj_a: Trajectory, out_a: str, traj_b: Trajectory, out_b: str) -> dict:
        system = "You are a Judge. Compare A and B and return JSON {'winner': 'A'/'B'/'tie', 'rationale': ''}."
        user = f"Task: {task.prompt}\nA: {out_a}\nB: {out_b}"
        
        try:
            response, in_tokens, out_tokens = await self.llm_strategy.client.complete(system, user, max_tokens=300)
            self.llm_strategy.budget_tracker.record(in_tokens, out_tokens)
            import json
            data = json.loads(response)
            data["cost_usd"] = self.llm_strategy.budget_tracker.total_spent
            return data
        except Exception as e:
            return {"winner": "tie", "rationale": f"Pairwise evaluation failed: {str(e)}", "cost_usd": 0.0}
