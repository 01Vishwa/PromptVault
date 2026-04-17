"""Shared async SQLAlchemy engine and session factory.

Both ``services/agent_eval`` and ``services/metrics`` import from here so that
a single DatabaseConnection class is the authoritative source of truth for the
connection pool — avoiding cross-service infrastructure imports at runtime.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from infrastructure.db.models import Base


class DatabaseConnection:
    """Manages the async SQLAlchemy engine and session factory.

    Call ``await DatabaseConnection.initialise(url)`` once at startup
    (inside the FastAPI lifespan), then use ``DatabaseConnection.get_session()``
    as an async context manager wherever a session is needed.
    """

    _engine: AsyncEngine | None = None
    _session_factory: async_sessionmaker[AsyncSession] | None = None

    @classmethod
    async def initialise(cls, database_url: str) -> None:
        """Create the engine and session factory.  Safe to call multiple times."""
        if cls._engine is not None:
            return
        cls._engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        cls._session_factory = async_sessionmaker(
            bind=cls._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    @classmethod
    @asynccontextmanager
    async def get_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """Yield a transactional async session.

        Commits on clean exit, rolls back on exception, always closes.
        """
        if cls._session_factory is None:
            raise RuntimeError(
                "DatabaseConnection not initialised. Call await initialise() first."
            )
        async with cls._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @classmethod
    async def create_tables(cls) -> None:
        """Create all ORM-mapped tables (use Alembic in production)."""
        if cls._engine is None:
            raise RuntimeError("DatabaseConnection not initialised.")
        async with cls._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @classmethod
    async def close(cls) -> None:
        """Dispose the engine and reset state."""
        if cls._engine is not None:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None
