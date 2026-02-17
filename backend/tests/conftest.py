# backend/tests/conftest.py
"""
Test fixtures for PromptVault.

Strategy: mock the Supabase client at the dependency level so tests
run without a live database. The JWT auth is also bypassed via
dependency overrides.
"""
from __future__ import annotations

import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ── Fake user for auth overrides ──────────────────────────────────────────────
TEST_USER_ID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
TEST_TOKEN = "test-jwt-token"


@pytest.fixture
def random_slug() -> str:
    return f"test-{uuid.uuid4().hex[:8]}"


def _make_supabase_mock() -> MagicMock:
    """Create a mock Supabase client with chainable .table().select()... API."""
    client = MagicMock()

    def _table(name: str) -> MagicMock:
        table = MagicMock()
        # Make all filter methods return the table itself (chainable)
        for method in ("select", "insert", "update", "upsert", "delete",
                       "eq", "neq", "ilike", "order", "limit"):
            getattr(table, method).return_value = table
        # .execute() returns a result with .data
        table.execute.return_value = MagicMock(data=[])
        return table

    client.table.side_effect = _table
    return client


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Async test client with auth + Supabase mocked out.
    Tests hit real FastAPI routes but skip the live DB.
    """
    from app.core.auth import get_access_token, get_current_user_id
    from app.main import app

    # Override auth dependencies
    app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID
    app.dependency_overrides[get_access_token] = lambda: TEST_TOKEN

    # Patch get_user_client AND get_supabase_client to return our mock
    with (
        patch("app.api.v1.prompts.get_user_client", return_value=_make_supabase_mock()),
        patch("app.api.v1.versions.get_user_client", return_value=_make_supabase_mock()),
        patch("app.api.v1.deployments.get_user_client", return_value=_make_supabase_mock()),
        patch("app.api.v1.execute.get_user_client", return_value=_make_supabase_mock()),
        patch("app.api.v1.serve.get_supabase_client", return_value=_make_supabase_mock()),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def supabase_mock() -> MagicMock:
    """Standalone Supabase client mock for unit-testing services directly."""
    return _make_supabase_mock()
