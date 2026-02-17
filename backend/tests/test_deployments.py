# backend/tests/test_deployments.py
"""Tests for the Deployments API endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_USER_ID


def _deployment_row(prompt_id: str | None = None, **overrides):
    base = {
        "id": str(uuid.uuid4()),
        "prompt_id": prompt_id or str(uuid.uuid4()),
        "prompt_version_id": str(uuid.uuid4()),
        "environment": "production",
        "deployed_by": str(TEST_USER_ID),
        "deployed_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_deploy(client: AsyncClient) -> None:
    prompt_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    row = _deployment_row(prompt_id=prompt_id, prompt_version_id=version_id)

    with patch("app.services.deployment.DeploymentService.deploy") as mock_deploy:
        from app.schemas.deployment import DeploymentRead

        mock_deploy.return_value = DeploymentRead(**row)
        resp = await client.post(
            f"/api/v1/prompts/{prompt_id}/deployments",
            json={
                "prompt_version_id": version_id,
                "environment": "production",
            },
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["environment"] == "production"
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_list_deployments(client: AsyncClient) -> None:
    prompt_id = str(uuid.uuid4())

    with patch("app.services.deployment.DeploymentService.list_for_prompt") as mock_list:
        from app.schemas.deployment import DeploymentList, DeploymentRead

        mock_list.return_value = DeploymentList(
            items=[DeploymentRead(**_deployment_row(prompt_id=prompt_id))],
            total=1,
        )
        resp = await client.get(f"/api/v1/prompts/{prompt_id}/deployments")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_undeploy(client: AsyncClient) -> None:
    prompt_id = str(uuid.uuid4())

    with patch("app.services.deployment.DeploymentService.undeploy") as mock_undeploy:
        mock_undeploy.return_value = None
        resp = await client.delete(
            f"/api/v1/prompts/{prompt_id}/deployments/production"
        )
    assert resp.status_code == 204
