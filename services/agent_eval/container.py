from .config import Settings
from .domain.events.domain_events import EventBus
import httpx

class Container:
    """Wires all dependencies together. Single instance per app lifetime."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._event_bus = EventBus.get_instance()
    
    def _build_db_repos(self, session):
        from .infrastructure.database.repositories.postgres_run_repository import PostgresRunRepository
        from .infrastructure.database.repositories.postgres_trajectory_repository import PostgresTrajectoryRepository
        return (
            PostgresRunRepository(session),
            PostgresTrajectoryRepository(session)
        )

    async def build_eval_service(self, session) -> "EvalService":
        """Build a fully-wired EvalService for a given DB session.
        
        Use this inside async contexts (request handlers, Celery tasks)
        where a live session is available.
        """
        from .application.services.eval_service import EvalService
        from .application.use_cases.run_eval_task import RunEvalTaskUseCase
        from .application.use_cases.run_eval_suite import RunEvalSuiteUseCase
        from .infrastructure.agents.agent_factory import AgentFactory

        run_repo, traj_repo = self._build_db_repos(session)
        agent_factory = AgentFactory(api_key=self.settings.anthropic_api_key)
        run_task = RunEvalTaskUseCase(
            agent_factory, run_repo, traj_repo, self._event_bus,
            timeout_seconds=self.settings.eval_task_timeout,
        )
        run_suite = RunEvalSuiteUseCase(run_task, self._event_bus)
        judge_client = httpx.AsyncClient()
        return EvalService(
            run_suite, run_task, run_repo, judge_client,
            self.settings.judge_service_url,
        )

    @property
    def eval_service(self):
        """Deprecated: use await container.build_eval_service(session) instead."""
        raise RuntimeError(
            "Container.eval_service requires a DB session. "
            "Call `await container.build_eval_service(session)` instead."
        )

    @property
    def task_service(self):
        # To be implemented in Phase 2
        pass

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus
