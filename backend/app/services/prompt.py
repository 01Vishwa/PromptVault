# backend/app/services/prompt.py
"""
Prompt service — CRUD operations against Supabase.
All DB access goes through the Supabase client (RLS-enforced).
"""
from __future__ import annotations

import uuid
from typing import Optional

from supabase import Client

from app.schemas.prompt import PromptCreate, PromptList, PromptRead, PromptUpdate


class PromptService:
    """Stateless service — receives a user-scoped Supabase client per request."""

    def __init__(self, client: Client) -> None:
        self._db = client

    async def create(self, user_id: uuid.UUID, payload: PromptCreate) -> PromptRead:
        data = {
            "user_id": str(user_id),
            "name": payload.name,
            "slug": payload.slug,
            "description": payload.description,
            "tags": payload.tags or [],
        }
        result = self._db.table("prompts").insert(data).execute()
        row = result.data[0]
        return PromptRead(**row)

    async def list(
        self,
        user_id: uuid.UUID,
        search: Optional[str] = None,
        include_archived: bool = False,
    ) -> PromptList:
        query = self._db.table("prompts").select("*").eq("user_id", str(user_id))
        if not include_archived:
            query = query.eq("is_archived", False)
        if search:
            query = query.ilike("name", f"%{search}%")
        query = query.order("updated_at", desc=True)
        result = query.execute()

        # Enrich with latest_version number
        items = []
        for row in result.data:
            prompt = PromptRead(**row)
            # Get max version_number for this prompt
            ver_result = (
                self._db.table("prompt_versions")
                .select("version_number")
                .eq("prompt_id", str(prompt.id))
                .order("version_number", desc=True)
                .limit(1)
                .execute()
            )
            if ver_result.data:
                prompt.latest_version = ver_result.data[0]["version_number"]
            items.append(prompt)

        return PromptList(items=items, total=len(items))

    async def get(self, prompt_id: uuid.UUID) -> Optional[PromptRead]:
        result = (
            self._db.table("prompts")
            .select("*")
            .eq("id", str(prompt_id))
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        return PromptRead(**result.data[0])

    async def get_by_slug(self, slug: str) -> Optional[PromptRead]:
        result = (
            self._db.table("prompts")
            .select("*")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        return PromptRead(**result.data[0])

    async def update(self, prompt_id: uuid.UUID, payload: PromptUpdate) -> PromptRead:
        update_data = payload.model_dump(exclude_unset=True)
        result = (
            self._db.table("prompts")
            .update(update_data)
            .eq("id", str(prompt_id))
            .execute()
        )
        return PromptRead(**result.data[0])

    async def delete(self, prompt_id: uuid.UUID) -> None:
        self._db.table("prompts").delete().eq("id", str(prompt_id)).execute()
