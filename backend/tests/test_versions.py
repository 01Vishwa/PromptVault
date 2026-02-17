# backend/tests/test_versions.py
"""Tests for the Versions API endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_USER_ID


def _version_row(prompt_id: str | None = None, version_number: int = 1, **overrides):
    base = {
        "id": str(uuid.uuid4()),
        "prompt_id": prompt_id or str(uuid.uuid4()),
        "version_number": version_number,
        "version_hash": "abc123" * 10,
        "template_text": "Hello {{name}}!",
        "system_prompt": None,
        "variables": ["name"],
        "model_config": None,
        "commit_message": "initial version",
        "author_id": str(TEST_USER_ID),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_create_version(client: AsyncClient) -> None:
    prompt_id = str(uuid.uuid4())
    row = _version_row(prompt_id=prompt_id)

    with patch("app.services.version.VersionService.create") as mock_create:
        from app.schemas.version import VersionRead

        mock_create.return_value = VersionRead(**row)
        resp = await client.post(
            f"/api/v1/prompts/{prompt_id}/versions",
            json={
                "template_text": "Hello {{name}}!",
                "commit_message": "initial version",
            },
        )
    assert resp.status_code == 201
    assert resp.json()["version_number"] == 1


@pytest.mark.asyncio
async def test_list_versions(client: AsyncClient) -> None:
    prompt_id = str(uuid.uuid4())

    with patch("app.services.version.VersionService.list") as mock_list:
        from app.schemas.version import VersionList, VersionRead

        mock_list.return_value = VersionList(
            items=[VersionRead(**_version_row(prompt_id=prompt_id))],
            total=1,
        )
        resp = await client.get(f"/api/v1/prompts/{prompt_id}/versions")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_diff_versions(client: AsyncClient) -> None:
    prompt_id = str(uuid.uuid4())
    v1 = _version_row(prompt_id=prompt_id, version_number=1, template_text="Hello {{name}}!")
    v2 = _version_row(prompt_id=prompt_id, version_number=2, template_text="Hi {{name}}, welcome!")

    with (
        patch("app.services.version.VersionService.get_by_number") as mock_get,
        patch("app.services.diff.DiffService.compute") as mock_diff,
    ):
        from app.schemas.version import VersionDiff, VersionRead

        mock_get.side_effect = [VersionRead(**v1), VersionRead(**v2)]
        mock_diff.return_value = VersionDiff(
            from_version=1,
            to_version=2,
            unified_diff="--- v1\n+++ v2\n@@ ...",
            char_patches="@@ ...",
            from_text=v1["template_text"],
            to_text=v2["template_text"],
        )
        resp = await client.get(f"/api/v1/prompts/{prompt_id}/versions/1/diff/2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["from_version"] == 1
    assert body["to_version"] == 2
