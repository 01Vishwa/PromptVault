from typing import Callable, Coroutine, Optional
import asyncio
from datetime import datetime
from uuid import uuid4

from ...domain.entities.task import Task
from ...domain.entities.eval_run import EvalRun
from ...domain.repositories.base import AbstractRunRepository, AbstractTrajectoryRepository
from ...domain.events.domain_events import EventBus
from ...infrastructure.agents.agent_factory import AgentFactory
from ...infrastructure.observability.logger import StructuredLogger
from ...infrastructure.observability.middleware import HarnessCallbackHandler, TrajectoryCollector
from core.errors.exceptions import AgentTimeoutError
from core.domain.types import RunStatus
from contracts.events.events import TaskCompleted

class RunEvalTaskUseCase:
    """Orchestrates one task evaluation end-to-end."""
    def __init__(self, agent_factory: AgentFactory,
                 run_repo: AbstractRunRepository,
                 traj_repo: AbstractTrajectoryRepository,
                 event_bus: EventBus,
                 timeout_seconds: int = 60):
        self.agent_factory = agent_factory
        self.run_repo = run_repo
        self.traj_repo = traj_repo
        self.event_bus = event_bus
        self.timeout_seconds = timeout_seconds

    async def execute(self, task: Task) -> EvalRun:
        run_id = str(uuid4())
        
        run = EvalRun(
            run_id=run_id,
            task_id=task.task_id,
            agent_version="v1.0",
            status=RunStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        await self.run_repo.save(run)

        logger = StructuredLogger(run_id=run_id)
        collector = TrajectoryCollector(run_id=run_id, task_id=task.task_id, min_steps=task.min_steps)
        harness = HarnessCallbackHandler(run_id, logger, collector, self.event_bus)

        agent = self.agent_factory.create()

        try:
            with logger:
                # Run the agent in asyncio wait_for bound
                result = await asyncio.wait_for(
                    agent.ainvoke({"input": task.prompt}, config={"callbacks": [harness]}),
                    timeout=self.timeout_seconds
                )
            
            # Save specific trajectory
            traj = await collector.save(self.run_repo, self.traj_repo, "PASS")
            run.attach_trajectory(traj)
            run.complete(RunStatus.PASS, "Agent finished normally")
            
        except asyncio.TimeoutError:
            logger.error("Timeout", f"Exceeded {self.timeout_seconds}s")
            run.complete(RunStatus.ERROR, "Agent timeout")
            
        except Exception as e:
            logger.error("Exception", str(e))
            run.complete(RunStatus.ERROR, str(e))
            
        finally:
            await self.run_repo.save(run)

        return run
