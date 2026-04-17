"""Concrete PostgreSQL repository for Trajectory domain entities."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.agent_eval.domain.entities.trajectory import Trajectory
from services.agent_eval.domain.repositories.base import AbstractTrajectoryRepository
from infrastructure.db.models import TrajectoryModel


class PostgresTrajectoryRepository(AbstractTrajectoryRepository):
    """Implements AbstractTrajectoryRepository against PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, trajectory: Trajectory, run_id: str) -> None:
        """Upsert a trajectory row keyed on *trajectory_id*."""
        existing = await self._session.get(TrajectoryModel, trajectory.trajectory_id)
        if existing is None:
            model = TrajectoryModel.from_domain(trajectory)
            self._session.add(model)
        else:
            existing.spans = [s.to_dict() for s in trajectory.spans]
            existing.final_output = trajectory.final_output
        await self._session.flush()

    async def get_by_run_id(self, run_id: str) -> Optional[Trajectory]:
        """Return the Trajectory associated with *run_id*, or None."""
        stmt = select(TrajectoryModel).where(TrajectoryModel.run_id == run_id)
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return model.to_domain() if model else None

