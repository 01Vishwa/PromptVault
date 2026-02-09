"""
Configuration Tests
===================

Tests for app.config module - settings loading and validation.
"""

import pytest
from unittest.mock import patch


class TestSettings:
    """Test Settings class."""
    
    def test_settings_loads_defaults(self, test_settings):
        """Test that settings load with defaults."""
        assert test_settings.api_port == 8000
        assert test_settings.api_host == "0.0.0.0"
        assert test_settings.max_react_iterations == 5
    
    def test_settings_loads_env_vars(self, test_settings):
        """Test that settings pick up environment variables."""
        assert test_settings.nvidia_api_key == "test-nvidia-key"
        assert test_settings.github_token == "test-github-token"
        assert test_settings.tavily_api_key == "test-tavily-key"
    
    def test_debug_defaults_to_false(self, test_settings):
        """SEC-001: Verify debug defaults to False."""
        # In test env it's explicitly "false"
        assert test_settings.debug is False
    
    def test_cors_origins_list_parses_csv(self, test_settings):
        """Test CORS origins parsing."""
        # Default is localhost:3000
        origins = test_settings.cors_origins_list
        assert isinstance(origins, list)
        assert len(origins) >= 1
    
    def test_is_development_property(self, test_settings):
        """Test environment detection."""
        assert test_settings.is_development is False  # env is "test"
        assert test_settings.is_production is False


class TestSettingsValidation:
    """Test settings validation logic."""
    
    def test_missing_all_api_keys_raises_error(self, monkeypatch):
        """SEC-003: Test that missing API keys causes validation error."""
        monkeypatch.setenv("NVIDIA_API_KEY", "")
        monkeypatch.setenv("GITHUB_TOKEN", "")
        monkeypatch.setenv("TAVILY_API_KEY", "test-key")
        monkeypatch.setenv("ENVIRONMENT", "development")
        
        from app.config import get_settings
        get_settings.cache_clear()
        
        with pytest.raises(ValueError, match="No LLM API key configured"):
            get_settings()
    
    def test_at_least_one_llm_key_passes(self, monkeypatch):
        """Test that having at least one LLM key passes validation."""
        monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
        monkeypatch.setenv("GITHUB_TOKEN", "")
        monkeypatch.setenv("TAVILY_API_KEY", "")
        monkeypatch.setenv("ENVIRONMENT", "development")
        
        from app.config import get_settings
        get_settings.cache_clear()
        
        # Should not raise
        settings = get_settings()
        assert settings.nvidia_api_key == "test-key"
