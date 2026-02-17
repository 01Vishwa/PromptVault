# backend/app/api/v1/versions.py
"""Prompt-version CRUD + diff router."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_access_token, get_current_user_id
from app.core.supabase import get_user_client
from app.schemas.version import VersionCreate, VersionDiff, VersionList, VersionRead
from app.services.diff import DiffService
from app.services.version import VersionService

router = APIRouter(prefix="/prompts/{prompt_id}/versions", tags=["versions"])


def _svc(token: str = Depends(get_access_token)) -> VersionService:
    return VersionService(get_user_client(token))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=VersionRead)
async def create_version(
    prompt_id: uuid.UUID,
    body: VersionCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    svc: VersionService = Depends(_svc),
):
    return await svc.create(prompt_id, user_id, body)


@router.get("", response_model=VersionList)
async def list_versions(
    prompt_id: uuid.UUID,
    svc: VersionService = Depends(_svc),
    _user: uuid.UUID = Depends(get_current_user_id),
):
    return await svc.list(prompt_id)


@router.get("/{version_id}", response_model=VersionRead)
async def get_version(
    version_id: uuid.UUID,
    svc: VersionService = Depends(_svc),
    _user: uuid.UUID = Depends(get_current_user_id),
    prompt_id: uuid.UUID = ...,  # path param (not used directly, but present in URL)
):
    version = await svc.get(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.get(
    "/{from_number}/diff/{to_number}",
    response_model=VersionDiff,
    summary="Diff two versions by version number",
)
async def diff_versions(
    prompt_id: uuid.UUID,
    from_number: int,
    to_number: int,
    svc: VersionService = Depends(_svc),
    _user: uuid.UUID = Depends(get_current_user_id),
):
    from_ver = await svc.get_by_number(prompt_id, from_number)
    to_ver = await svc.get_by_number(prompt_id, to_number)
    if not from_ver or not to_ver:
        raise HTTPException(status_code=404, detail="One or both versions not found")
    return DiffService.compute(
        from_version=from_ver.version_number,
        to_version=to_ver.version_number,
        from_text=from_ver.template_text,
        to_text=to_ver.template_text,
    )
