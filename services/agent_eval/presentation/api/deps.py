from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from ...infrastructure.database.connection import DatabaseConnection
from ...infrastructure.database.repositories.postgres_run_repository import PostgresRunRepository
from ...infrastructure.database.repositories.postgres_trajectory_repository import PostgresTrajectoryRepository
from ...application.services.eval_service import EvalService
from ...container import Container
from ...config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
container = Container(get_settings())

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with DatabaseConnection.get_session() as session:
        yield session

async def get_run_repo(session: AsyncSession = Depends(get_db_session)) -> PostgresRunRepository:
    return PostgresRunRepository(session)

async def get_traj_repo(session: AsyncSession = Depends(get_db_session)) -> PostgresTrajectoryRepository:
    return PostgresTrajectoryRepository(session)

async def get_eval_service(run_repo: PostgresRunRepository = Depends(get_run_repo), 
                           traj_repo: PostgresTrajectoryRepository = Depends(get_traj_repo)) -> EvalService:
    from ...application.use_cases.run_eval_task import RunEvalTaskUseCase
    from ...application.use_cases.run_eval_suite import RunEvalSuiteUseCase
    from ...infrastructure.agents.agent_factory import AgentFactory
    import httpx
    
    settings = get_settings()
    agent_factory = AgentFactory(api_key=settings.anthropic_api_key)
    event_bus = container.event_bus
    
    run_task = RunEvalTaskUseCase(agent_factory, run_repo, traj_repo, event_bus)
    run_suite = RunEvalSuiteUseCase(run_task, event_bus)
    judge_client = httpx.AsyncClient()
    
    return EvalService(run_suite, run_task, run_repo, judge_client, settings.judge_service_url)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="Invalid auth credentials")
    return {"user": "admin"}
