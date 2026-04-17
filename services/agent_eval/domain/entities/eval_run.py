from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from core.domain.types import RunStatus
from .trajectory import Trajectory

@dataclass
class EvalRun:
    run_id: str
    task_id: str
    agent_version: str
    status: RunStatus
    started_at: datetime
    trajectory: Optional[Trajectory] = None
    score: Optional[float] = None
    ended_at: Optional[datetime] = None
    exit_reason: str = ""

    @property
    def duration_ms(self) -> int:
        end = self.ended_at or datetime.utcnow()
        return int((end - self.started_at).total_seconds() * 1000)

    def complete(self, status: RunStatus, exit_reason: str) -> None:
        self.status = status
        self.exit_reason = exit_reason
        self.ended_at = datetime.utcnow()

    def attach_trajectory(self, trajectory: Trajectory) -> None:
        self.trajectory = trajectory

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "agent_version": self.agent_version,
            "status": self.status.value if isinstance(self.status, RunStatus) else self.status,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "exit_reason": self.exit_reason,
            "score": self.score,
            "trajectory": self.trajectory.to_dict() if self.trajectory else None
        }
