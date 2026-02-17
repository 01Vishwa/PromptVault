# backend/app/api/v1/execute.py
"""LLM execution router — authenticated, multi-provider."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_access_token, get_current_user_id
from app.core.supabase import get_user_client
from app.schemas.execution import ExecuteRequest, MultiExecutionResponse
from app.services.llm import LLMService
from app.services.parser import render_template
from app.services.version import VersionService

router = APIRouter(prefix="/execute", tags=["execute"])


@router.post("", response_model=MultiExecutionResponse)
async def execute(
    body: ExecuteRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    token: str = Depends(get_access_token),
):
    client = get_user_client(token)
    ver_svc = VersionService(client)
    llm_svc = LLMService(client)

    # Fetch the prompt version
    version = await ver_svc.get(body.prompt_version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Prompt version not found")

    # Render the template
    rendered = render_template(version.template_text, body.variables)

    # Resolve config override
    config = body.model_config_override or version.llm_config or {}

    # Execute against all requested providers in parallel
    results = await llm_svc.execute_multi(
        models=body.providers,
        rendered_prompt=rendered,
        system_prompt=version.system_prompt,
        config_override=config,
        prompt_version_id=version.id,
        user_id=user_id,
    )

    return MultiExecutionResponse(
        prompt_version_id=version.id,
        rendered_prompt=rendered,
        results=results,
    )
