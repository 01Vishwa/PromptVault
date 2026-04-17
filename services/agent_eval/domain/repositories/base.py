from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities.eval_run import EvalRun
from ..entities.trajectory import Trajectory

class AbstractRunRepository(ABC):
    @abstractmethod
    async def save(self, run: EvalRun) -> None:
        pass

    @abstractmethod
    async def get_by_id(self, run_id: str) -> Optional[EvalRun]:
        pass

    @abstractmethod
    async def list(self, limit: int, offset: int, status: Optional[str] = None) -> List[EvalRun]:
        pass

    @abstractmethod
    async def get_latest_by_task(self, task_id: str) -> Optional[EvalRun]:
        pass

class AbstractTrajectoryRepository(ABC):
    @abstractmethod
    async def save(self, trajectory: Trajectory, run_id: str) -> None:
        pass

    @abstractmethod
    async def get_by_run_id(self, run_id: str) -> Optional[Trajectory]:
        pass

class AbstractGoldenSetRepository(ABC):
    @abstractmethod
    async def save_annotation(self, annotation: dict) -> None:
        pass

    @abstractmethod
    async def list_unannotated(self, limit: int) -> List[dict]:
        pass
