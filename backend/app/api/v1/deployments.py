# backend/app/api/v1/deployments.py
"""Deployment management router — authenticated."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_access_token, get_current_user_id
from app.core.supabase import get_user_client
from app.schemas.deployment import DeploymentList, DeploymentRead, DeployRequest
from app.services.deployment import DeploymentService

router = APIRouter(prefix="/prompts/{prompt_id}/deployments", tags=["deployments"])


def _svc(token: str = Depends(get_access_token)) -> DeploymentService:
    return DeploymentService(get_user_client(token))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DeploymentRead)
async def deploy(
    prompt_id: uuid.UUID,
    body: DeployRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    svc: DeploymentService = Depends(_svc),
):
    return await svc.deploy(prompt_id, user_id, body)


@router.get("", response_model=DeploymentList)
async def list_deployments(
    prompt_id: uuid.UUID,
    svc: DeploymentService = Depends(_svc),
    _user: uuid.UUID = Depends(get_current_user_id),
):
    return await svc.list_for_prompt(prompt_id)


@router.delete(
    "/{environment}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate deployment for environment",
)
async def undeploy(
    prompt_id: uuid.UUID,
    environment: str,
    svc: DeploymentService = Depends(_svc),
    _user: uuid.UUID = Depends(get_current_user_id),
):
    await svc.undeploy(prompt_id, environment)
