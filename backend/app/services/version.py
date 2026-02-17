# backend/app/services/version.py
"""
Version service — immutable prompt version creation, listing, retrieval.
Every save creates an append-only version. SHA-256 hash prevents duplicates.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Optional

from supabase import Client

from app.schemas.version import VersionCreate, VersionList, VersionRead
from app.services.parser import extract_variables


class VersionService:
    def __init__(self, client: Client) -> None:
        self._db = client

    @staticmethod
    def compute_hash(
        template_text: str,
        system_prompt: Optional[str],
        model_config: Optional[dict],
    ) -> str:
        """Deterministic hash: SHA-256(template + system + sorted-config)."""
        config_str = json.dumps(model_config or {}, sort_keys=True, ensure_ascii=False)
        system_str = system_prompt or ""
        payload = f"{template_text}\x00{system_str}\x00{config_str}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def create(
        self,
        prompt_id: uuid.UUID,
        author_id: uuid.UUID,
        payload: VersionCreate,
    ) -> VersionRead:
        """Create a new immutable version. Idempotent — duplicate hash returns existing."""
        model_cfg = payload.model_config_data.model_dump() if payload.model_config_data else None
        version_hash = self.compute_hash(
            payload.template_text,
            payload.system_prompt,
            model_cfg,
        )

        # Check for duplicate hash (idempotency)
        existing = (
            self._db.table("prompt_versions")
            .select("*")
            .eq("prompt_id", str(prompt_id))
            .eq("version_hash", version_hash)
            .limit(1)
            .execute()
        )
        if existing.data:
            return VersionRead(**existing.data[0])

        # Get next version number
        max_ver = (
            self._db.table("prompt_versions")
            .select("version_number")
            .eq("prompt_id", str(prompt_id))
            .order("version_number", desc=True)
            .limit(1)
            .execute()
        )
        next_number = (max_ver.data[0]["version_number"] + 1) if max_ver.data else 1

        # Auto-detect variables
        variables = extract_variables(payload.template_text)

        data = {
            "prompt_id": str(prompt_id),
            "version_number": next_number,
            "version_hash": version_hash,
            "template_text": payload.template_text,
            "system_prompt": payload.system_prompt,
            "variables": variables,
            "model_config": model_cfg,
            "commit_message": payload.commit_message,
            "author_id": str(author_id),
        }
        result = self._db.table("prompt_versions").insert(data).execute()
        return VersionRead(**result.data[0])

    async def list(self, prompt_id: uuid.UUID) -> VersionList:
        result = (
            self._db.table("prompt_versions")
            .select("*")
            .eq("prompt_id", str(prompt_id))
            .order("version_number", desc=True)
            .execute()
        )
        items = [VersionRead(**row) for row in result.data]
        return VersionList(items=items, total=len(items))

    async def get(self, version_id: uuid.UUID) -> Optional[VersionRead]:
        result = (
            self._db.table("prompt_versions")
            .select("*")
            .eq("id", str(version_id))
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        return VersionRead(**result.data[0])

    async def get_by_number(
        self, prompt_id: uuid.UUID, version_number: int
    ) -> Optional[VersionRead]:
        result = (
            self._db.table("prompt_versions")
            .select("*")
            .eq("prompt_id", str(prompt_id))
            .eq("version_number", version_number)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        return VersionRead(**result.data[0])
