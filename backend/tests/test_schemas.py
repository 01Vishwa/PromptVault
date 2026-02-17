# backend/tests/test_schemas.py
"""Schema validation tests — no I/O, just Pydantic round-trips."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.prompt import PromptCreate, PromptRead
from app.schemas.version import ModelConfig, VersionCreate, VersionDiff, VersionRead
from app.schemas.deployment import DeployRequest, DeploymentRead
from app.schemas.execution import ExecuteRequest, ExecutionResult, ServeRequest


def test_prompt_create_valid() -> None:
    p = PromptCreate(name="Test", slug="test-prompt", tags=["qa"])
    assert p.name == "Test"
    assert p.slug == "test-prompt"


def test_prompt_create_invalid_slug() -> None:
    with pytest.raises(ValidationError):
        PromptCreate(name="Test", slug="Invalid Slug!")


def test_version_create_blank_template_rejected() -> None:
    with pytest.raises(ValidationError):
        VersionCreate(template_text="   ", commit_message="test")


def test_version_create_valid() -> None:
    vc = VersionCreate(
        template_text="Hello {{name}}!",
        commit_message="initial",
        model_config_data=ModelConfig(temperature=0.7, max_tokens=100),
    )
    assert vc.template_text == "Hello {{name}}!"
    assert vc.model_config_data is not None
    assert vc.model_config_data.temperature == 0.7


def test_version_read_with_alias() -> None:
    """Ensure the model_config alias works correctly."""
    data = {
        "id": str(uuid.uuid4()),
        "prompt_id": str(uuid.uuid4()),
        "version_number": 1,
        "version_hash": "abc123",
        "template_text": "test",
        "system_prompt": None,
        "variables": [],
        "model_config": {"temperature": 0.5},
        "commit_message": "init",
        "author_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    vr = VersionRead(**data)
    assert vr.llm_config == {"temperature": 0.5}


def test_deploy_request_valid_environments() -> None:
    for env in ("production", "staging", "development"):
        dr = DeployRequest(
            prompt_version_id=uuid.uuid4(),
            environment=env,
        )
        assert dr.environment == env


def test_deploy_request_invalid_environment() -> None:
    with pytest.raises(ValidationError):
        DeployRequest(prompt_version_id=uuid.uuid4(), environment="invalid")


def test_execute_request_requires_providers() -> None:
    with pytest.raises(ValidationError):
        ExecuteRequest(prompt_version_id=uuid.uuid4(), providers=[])


def test_serve_request_defaults() -> None:
    sr = ServeRequest()
    assert sr.variables == {}
    assert sr.model is None
