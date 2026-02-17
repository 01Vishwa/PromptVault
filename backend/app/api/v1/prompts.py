# backend/app/api/v1/prompts.py
"""Prompt CRUD router."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import get_access_token, get_current_user_id
from app.core.supabase import get_user_client
from app.schemas.prompt import PromptCreate, PromptList, PromptRead, PromptUpdate
from app.services.prompt import PromptService

router = APIRouter(prefix="/prompts", tags=["prompts"])


def _svc(token: str = Depends(get_access_token)) -> PromptService:
    return PromptService(get_user_client(token))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PromptRead)
async def create_prompt(
    body: PromptCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    svc: PromptService = Depends(_svc),
):
    return await svc.create(user_id, body)


@router.get("", response_model=PromptList)
async def list_prompts(
    search: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    user_id: uuid.UUID = Depends(get_current_user_id),
    svc: PromptService = Depends(_svc),
):
    return await svc.list(user_id, search=search, include_archived=include_archived)


@router.get("/{prompt_id}", response_model=PromptRead)
async def get_prompt(
    prompt_id: uuid.UUID,
    svc: PromptService = Depends(_svc),
    _user: uuid.UUID = Depends(get_current_user_id),
):
    prompt = await svc.get(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.patch("/{prompt_id}", response_model=PromptRead)
async def update_prompt(
    prompt_id: uuid.UUID,
    body: PromptUpdate,
    svc: PromptService = Depends(_svc),
    _user: uuid.UUID = Depends(get_current_user_id),
):
    updated = await svc.update(prompt_id, body)
    if not updated:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return updated


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: uuid.UUID,
    svc: PromptService = Depends(_svc),
    _user: uuid.UUID = Depends(get_current_user_id),
):
    await svc.delete(prompt_id)
