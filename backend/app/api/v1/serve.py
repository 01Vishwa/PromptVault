# backend/app/api/v1/serve.py
"""
Public serve endpoint — NO authentication required.
Uses the service_role Supabase client (bypasses RLS).
Resolves the active deployment for the given slug + environment
and executes the prompt with the provided variables.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.supabase import get_supabase_client
from app.schemas.execution import ServeRequest, ServeResponse
from app.services.deployment import DeploymentService
from app.services.llm import LLMService
from app.services.parser import render_template
from app.services.version import VersionService

router = APIRouter(prefix="/serve", tags=["serve"])

DEFAULT_MODEL = "openai/gpt-4o-mini"


@router.post("/{slug}", response_model=ServeResponse)
async def serve_prompt(slug: str, body: ServeRequest):
    """
    Public endpoint: POST /api/v1/serve/{slug}
    Looks up the active production deployment for the prompt slug,
    renders the template, and calls the LLM.
    """
    client = get_supabase_client()  # service_role — bypasses RLS

    # Resolve prompt by slug
    prompt_result = (
        client.table("prompts")
        .select("id")
        .eq("slug", slug)
        .eq("is_archived", False)
        .limit(1)
        .execute()
    )
    if not prompt_result.data:
        raise HTTPException(status_code=404, detail=f"Prompt '{slug}' not found")
    prompt_id = prompt_result.data[0]["id"]

    # Get active production deployment
    deploy_svc = DeploymentService(client)
    deployment = await deploy_svc.get_active(prompt_id, environment="production")
    if not deployment:
        raise HTTPException(
            status_code=404,
            detail=f"No active production deployment for '{slug}'",
        )

    # Fetch the deployed version
    ver_svc = VersionService(client)
    version = await ver_svc.get(deployment.prompt_version_id)
    if not version:
        raise HTTPException(status_code=500, detail="Deployed version not found")

    # Render template
    rendered = render_template(version.template_text, body.variables)

    # Execute via LLM
    model = body.model or DEFAULT_MODEL
    config = version.llm_config or {}

    llm_svc = LLMService(client)
    # Use a system user ID for serve-endpoint executions
    import uuid

    system_user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    result = await llm_svc.execute_single(
        model=model,
        rendered_prompt=rendered,
        system_prompt=version.system_prompt,
        config_override=config,
        prompt_version_id=version.id,
        user_id=system_user_id,
    )

    if result.status == "error":
        raise HTTPException(status_code=502, detail=result.error_message or "LLM error")

    return ServeResponse(
        response=result.response_text or "",
        model=model,
        tokens_in=result.tokens_in or 0,
        tokens_out=result.tokens_out or 0,
        latency_ms=result.latency_ms or 0,
    )
