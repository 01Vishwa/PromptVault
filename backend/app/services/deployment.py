# backend/app/services/deployment.py
"""
Deployment service — manage deploy pointers.
Each (prompt, environment) pair has at most one active deployment.
Deploying = UPSERT the pointer to a new version.
"""
from __future__ import annotations

import uuid
from typing import Optional

from supabase import Client

from app.schemas.deployment import DeploymentList, DeploymentRead, DeployRequest


class DeploymentService:
    def __init__(self, client: Client) -> None:
        self._db = client

    async def deploy(
        self,
        prompt_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: DeployRequest,
    ) -> DeploymentRead:
        """
        Deploy (or re-deploy) a prompt version to an environment.
        Uses upsert on the (prompt_id, environment) unique constraint.
        """
        data = {
            "prompt_id": str(prompt_id),
            "prompt_version_id": str(payload.prompt_version_id),
            "environment": payload.environment,
            "deployed_by": str(user_id),
            "is_active": True,
        }
        result = (
            self._db.table("deployments")
            .upsert(data, on_conflict="prompt_id,environment")
            .execute()
        )
        return DeploymentRead(**result.data[0])

    async def get_active(
        self,
        prompt_id: uuid.UUID,
        environment: str = "production",
    ) -> Optional[DeploymentRead]:
        result = (
            self._db.table("deployments")
            .select("*")
            .eq("prompt_id", str(prompt_id))
            .eq("environment", environment)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        return DeploymentRead(**result.data[0])

    async def list_for_prompt(self, prompt_id: uuid.UUID) -> DeploymentList:
        result = (
            self._db.table("deployments")
            .select("*")
            .eq("prompt_id", str(prompt_id))
            .order("deployed_at", desc=True)
            .execute()
        )
        items = [DeploymentRead(**row) for row in result.data]
        return DeploymentList(items=items, total=len(items))

    async def undeploy(
        self,
        prompt_id: uuid.UUID,
        environment: str = "production",
    ) -> None:
        (
            self._db.table("deployments")
            .update({"is_active": False})
            .eq("prompt_id", str(prompt_id))
            .eq("environment", environment)
            .execute()
        )
