# backend/app/schemas/version.py
"""Pydantic schemas for PromptVersion operations."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ModelConfig(BaseModel):
    """LLM configuration parameters stored per version."""
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    stop_sequences: Optional[List[str]] = None


class VersionCreate(BaseModel):
    template_text: str = Field(..., min_length=1)
    system_prompt: Optional[str] = None
    model_config_data: Optional[ModelConfig] = None
    commit_message: str = Field(..., min_length=1, max_length=500)

    @field_validator("template_text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("template_text must not be blank")
        return v


class VersionRead(BaseModel):
    id: uuid.UUID
    prompt_id: uuid.UUID
    version_number: int
    version_hash: str
    template_text: str
    system_prompt: Optional[str]
    variables: List[str]
    llm_config: Optional[Dict[str, Any]] = Field(None, alias="model_config")
    commit_message: str
    author_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class VersionList(BaseModel):
    items: List[VersionRead]
    total: int


class VersionDiff(BaseModel):
    """Diff output between two prompt versions."""
    from_version: int
    to_version: int
    unified_diff: str          # line-level unified diff (difflib)
    char_patches: str          # character-level patches (diff-match-patch)
    from_text: str
    to_text: str
