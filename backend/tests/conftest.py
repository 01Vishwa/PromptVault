"""
Test Configuration and Fixtures
================================

Shared pytest fixtures and configuration for Axiom AI test suite.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# TEST-003: Mock LLM Client Fixture
# =============================================================================

@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response."""
    response = MagicMock()
    response.content = "This is a mock LLM response."
    response.tool_calls = []
    return response


@pytest.fixture
def mock_llm_client(mock_llm_response):
    """Create a mock LLM client for testing without live API calls."""
    client = MagicMock()
    client.chat = AsyncMock(return_value=mock_llm_response)
    client.stream_chat = AsyncMock(return_value=iter([
        {"type": "content", "data": {"delta": "Mock "}}
    ]))
    client.last_provider = MagicMock()
    client.last_provider.value = "mock"
    return client


@pytest.fixture
def mock_tool_result():
    """Create a mock tool result."""
    from app.tools.base import ToolResult
    return ToolResult(
        success=True,
        data="Mock tool result data",
        sources=[{"title": "Mock Source", "url": "https://example.com"}]
    )


# =============================================================================
# Environment Fixtures
# =============================================================================

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("NVIDIA_API_KEY", "test-nvidia-key")
    monkeypatch.setenv("GITHUB_TOKEN", "test-github-token")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DEBUG", "false")


@pytest.fixture
def test_settings(mock_env_vars):
    """Create test settings with mock environment."""
    # Clear cached settings
    from app.config import get_settings
    get_settings.cache_clear()
    return get_settings()
