"""Concrete PostgreSQL repository for EvalRun domain entities."""
from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.agent_eval.domain.entities.eval_run import EvalRun
from services.agent_eval.domain.repositories.base import AbstractRunRepository
from infrastructure.db.models import EvalRunModel


class PostgresRunRepository(AbstractRunRepository):
    """Implements AbstractRunRepository against a PostgreSQL database via
    SQLAlchemy 2.0 async ORM."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, run: EvalRun) -> None:
        """Upsert an EvalRun: insert if new, update if already persisted."""
        existing = await self._session.get(EvalRunModel, run.run_id)
        if existing is None:
            model = EvalRunModel.from_domain(run)
            self._session.add(model)
        else:
            existing.status = (
                run.status.value if hasattr(run.status, "value") else run.status
            )
            existing.ended_at = run.ended_at
            existing.exit_reason = run.exit_reason
            existing.score = run.score
        await self._session.flush()

    async def get_by_id(self, run_id: str) -> Optional[EvalRun]:
        """Return the domain EvalRun for *run_id*, or None if not found."""
        model = await self._session.get(EvalRunModel, run_id)
        return model.to_domain() if model else None

    async def list(
        self,
        limit: int = 20,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> list[EvalRun]:
        """Return up to *limit* runs ordered by start time descending."""
        stmt = (
            select(EvalRunModel)
            .order_by(EvalRunModel.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            stmt = stmt.where(EvalRunModel.status == status)
        result = await self._session.execute(stmt)
        rows: Sequence[EvalRunModel] = result.scalars().all()
        return [row.to_domain() for row in rows]

    async def get_latest_by_task(self, task_id: str) -> Optional[EvalRun]:
        """Return the most recent EvalRun for *task_id*, or None."""
        stmt = (
            select(EvalRunModel)
            .where(EvalRunModel.task_id == task_id)
            .order_by(EvalRunModel.started_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return model.to_domain() if model else None

