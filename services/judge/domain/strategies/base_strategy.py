from abc import ABC, abstractmethod
from ..entities.judge_result import JudgeResult
from services.agent_eval.domain.entities.task import Task
from services.agent_eval.domain.entities.trajectory import Trajectory

class JudgeStrategyBase(ABC):
    @abstractmethod
    async def evaluate(self, task: Task, trajectory: Trajectory, final_output: str) -> JudgeResult:
        pass
