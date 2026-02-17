# backend/app/schemas/execution.py
"""Pydantic schemas for LLM execution requests and logged results."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExecuteRequest(BaseModel):
    """Request to execute a prompt version against one or more providers."""
    prompt_version_id: uuid.UUID
    variables: Dict[str, str] = Field(default_factory=dict)
    providers: List[str] = Field(
        ...,
        min_length=1,
        description="List of LiteLLM model strings, e.g. ['openai/gpt-4o', 'anthropic/claude-3-sonnet-20240229']",
    )
    model_config_override: Optional[Dict[str, Any]] = None


class ExecutionResult(BaseModel):
    """Result from a single provider execution."""
    id: uuid.UUID
    model_provider: str
    model_name: str
    response_text: Optional[str]
    tokens_in: Optional[int]
    tokens_out: Optional[int]
    latency_ms: Optional[int]
    cost_estimate: Optional[float]
    status: str
    error_message: Optional[str]
    created_at: datetime


class MultiExecutionResponse(BaseModel):
    """Response from multi-provider parallel execution."""
    prompt_version_id: uuid.UUID
    rendered_prompt: str
    results: List[ExecutionResult]


class ServeRequest(BaseModel):
    """Public serve endpoint request body."""
    variables: Dict[str, str] = Field(default_factory=dict)
    model: Optional[str] = Field(
        None,
        description="Override the default model. E.g. 'openai/gpt-4o'",
    )


class ServeResponse(BaseModel):
    """Public serve endpoint response."""
    response: str
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
