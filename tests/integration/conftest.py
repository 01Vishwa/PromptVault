"""Pytest fixtures for integration tests."""
from __future__ import annotations

import os

import pytest
import pytest_asyncio
import httpx

from services.agent_eval.infrastructure.database.connection import DatabaseConnection
from services.agent_eval.infrastructure.agents.agent_factory import AgentFactory, AgentConfig
from services.agent_eval.domain.events.domain_events import EventBus
from services.agent_eval.infrastructure.database.repositories.postgres_run_repository import PostgresRunRepository
from services.agent_eval.infrastructure.database.repositories.postgres_trajectory_repository import PostgresTrajectoryRepository


TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:eval123@localhost:5432/agent_eval",
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    await DatabaseConnection.initialise(TEST_DATABASE_URL)
    await DatabaseConnection.create_tables()
    yield
    await DatabaseConnection.close()


@pytest_asyncio.fixture
async def db_session(db_engine):
    async with DatabaseConnection.get_session() as session:
        yield session


@pytest_asyncio.fixture
def run_repo(db_session):
    return PostgresRunRepository(db_session)


@pytest_asyncio.fixture
def traj_repo(db_session):
    return PostgresTrajectoryRepository(db_session)


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def agent_factory():
    if not ANTHROPIC_API_KEY:
        pytest.skip("ANTHROPIC_API_KEY not set — skipping agent factory test")
    return AgentFactory(api_key=ANTHROPIC_API_KEY)


@pytest_asyncio.fixture
async def auth_token():
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "http://localhost:8080/auth/token",
            json={"api_key": "test"},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()["access_token"]


@pytest_asyncio.fixture
async def httpx_client():
    async with httpx.AsyncClient(timeout=30) as client:
        yield client
