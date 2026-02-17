# backend/tests/test_prompts.py
"""Tests for the Prompts API endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_USER_ID


def _prompt_row(slug: str = "test-prompt", **overrides):
    """Build a fake Supabase prompt row dict."""
    base = {
        "id": str(uuid.uuid4()),
        "user_id": str(TEST_USER_ID),
        "name": "Test Prompt",
        "slug": slug,
        "description": "A test prompt",
        "tags": ["test"],
        "is_archived": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_create_prompt(client: AsyncClient, random_slug: str) -> None:
    """POST /api/v1/prompts should accept a valid payload."""
    row = _prompt_row(slug=random_slug)

    with patch("app.services.prompt.PromptService.create") as mock_create:
        from app.schemas.prompt import PromptRead

        mock_create.return_value = PromptRead(**row)
        resp = await client.post(
            "/api/v1/prompts",
            json={"name": "Test Prompt", "slug": random_slug, "tags": ["test"]},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == random_slug
    assert body["name"] == "Test Prompt"


@pytest.mark.asyncio
async def test_list_prompts(client: AsyncClient) -> None:
    """GET /api/v1/prompts should return a list."""
    with patch("app.services.prompt.PromptService.list") as mock_list:
        from app.schemas.prompt import PromptList, PromptRead

        mock_list.return_value = PromptList(
            items=[PromptRead(**_prompt_row())],
            total=1,
        )
        resp = await client.get("/api/v1/prompts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


@pytest.mark.asyncio
async def test_get_prompt_not_found(client: AsyncClient) -> None:
    """GET /api/v1/prompts/{id} should return 404 for missing prompt."""
    fake_id = str(uuid.uuid4())
    with patch("app.services.prompt.PromptService.get") as mock_get:
        mock_get.return_value = None
        resp = await client.get(f"/api/v1/prompts/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_prompt_found(client: AsyncClient) -> None:
    """GET /api/v1/prompts/{id} should return the prompt when it exists."""
    row = _prompt_row()
    prompt_id = row["id"]

    with patch("app.services.prompt.PromptService.get") as mock_get:
        from app.schemas.prompt import PromptRead

        mock_get.return_value = PromptRead(**row)
        resp = await client.get(f"/api/v1/prompts/{prompt_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == prompt_id


@pytest.mark.asyncio
async def test_delete_prompt(client: AsyncClient) -> None:
    """DELETE /api/v1/prompts/{id} should return 204."""
    fake_id = str(uuid.uuid4())
    with patch("app.services.prompt.PromptService.delete") as mock_delete:
        mock_delete.return_value = None
        resp = await client.delete(f"/api/v1/prompts/{fake_id}")
    assert resp.status_code == 204
