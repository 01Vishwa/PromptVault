from datetime import datetime
from typing import Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, UUID

class Base(DeclarativeBase):
    pass

class EvalRunModel(Base):
    __tablename__ = "eval_runs"

    run_id: Mapped[str] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column()
    agent_version: Mapped[str] = mapped_column()
    status: Mapped[str] = mapped_column()
    started_at: Mapped[datetime] = mapped_column()
    ended_at: Mapped[Optional[datetime]] = mapped_column()
    exit_reason: Mapped[str] = mapped_column(default="")
    score: Mapped[Optional[float]] = mapped_column()

    def to_domain(self):
        from services.agent_eval.domain.entities.eval_run import EvalRun
        from core.domain.types import RunStatus
        return EvalRun(
            run_id=self.run_id,
            task_id=self.task_id,
            agent_version=self.agent_version,
            status=RunStatus(self.status),
            started_at=self.started_at,
            ended_at=self.ended_at,
            exit_reason=self.exit_reason,
            score=self.score
        )

    @classmethod
    def from_domain(cls, entity):
        return cls(
            run_id=entity.run_id,
            task_id=entity.task_id,
            agent_version=entity.agent_version,
            status=entity.status.value if hasattr(entity.status, 'value') else entity.status,
            started_at=entity.started_at,
            ended_at=entity.ended_at,
            exit_reason=entity.exit_reason,
            score=entity.score
        )

class TrajectoryModel(Base):
    __tablename__ = "trajectories"

    trajectory_id: Mapped[str] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(unique=True)
    spans: Mapped[dict] = mapped_column(type_=JSONB)
    final_output: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column()

    def to_domain(self):
        from services.agent_eval.domain.entities.trajectory import Trajectory
        from services.agent_eval.domain.entities.span import Span
        spans = [Span(**s) for s in self.spans]
        return Trajectory(
            trajectory_id=self.trajectory_id,
            run_id=self.run_id,
            spans=spans,
            final_output=self.final_output,
            created_at=self.created_at
        )

    @classmethod
    def from_domain(cls, entity):
        return cls(
            trajectory_id=entity.trajectory_id,
            run_id=entity.run_id,
            spans=[s.to_dict() for s in entity.spans],
            final_output=entity.final_output,
            created_at=entity.created_at
        )

class JudgeScoreModel(Base):
    __tablename__ = "judge_scores"
    
    score_id: Mapped[str] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column()
    judge_model: Mapped[str] = mapped_column()
    score_value: Mapped[float] = mapped_column()
    reasoning: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column()

class GoldenSetModel(Base):
    __tablename__ = "golden_set"

    annotation_id: Mapped[str] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column()
    trajectory_hash: Mapped[str] = mapped_column()
    is_regression: Mapped[bool] = mapped_column()
    human_score: Mapped[Optional[float]] = mapped_column()
    notes: Mapped[Optional[str]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column()
