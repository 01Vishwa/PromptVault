# backend/app/schemas/prompt.py
"""Pydantic schemas for Prompt CRUD operations."""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class PromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    description: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9][a-z0-9_-]*$", v):
            raise ValueError("slug must be lowercase alphanumeric with hyphens/underscores")
        return v


class PromptUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_archived: Optional[bool] = None


class PromptRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    slug: str
    description: Optional[str]
    tags: List[str]
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    latest_version: Optional[int] = None  # populated by service

    model_config = {"from_attributes": True}


class PromptList(BaseModel):
    items: List[PromptRead]
    total: int
