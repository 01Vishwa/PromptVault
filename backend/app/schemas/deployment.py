# backend/app/schemas/deployment.py
"""Pydantic schemas for prompt deployment management."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DeployRequest(BaseModel):
    prompt_version_id: uuid.UUID
    environment: str = Field(
        default="production",
        pattern=r"^(production|staging|development)$",
    )


class DeploymentRead(BaseModel):
    id: uuid.UUID
    prompt_id: uuid.UUID
    prompt_version_id: uuid.UUID
    environment: str
    deployed_by: str  # user UUID stored as string in Supabase
    deployed_at: datetime
    is_active: bool
    version_number: Optional[int] = None  # joined from prompt_versions

    model_config = {"from_attributes": True}


class DeploymentList(BaseModel):
    items: List[DeploymentRead]
    total: int
