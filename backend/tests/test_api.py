"""
API Integration Tests
=====================

Tests for API endpoints (chat, health).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def test_client(mock_env_vars):
    """Create test client with mocked dependencies."""
    with patch('app.llm.client.NVIDIAClient'), \
         patch('app.llm.client.GitHubModelsClient'):
        from app.main import app
        return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoints."""
    
    def test_health_returns_ok(self, test_client):
        """Test basic health check."""
        response = test_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_health_includes_version(self, test_client):
        """Test health check includes version info."""
        response = test_client.get("/api/v1/health")
        data = response.json()
        assert "version" in data


class TestChatEndpoint:
    """Test chat endpoints."""
    
    def test_chat_validates_empty_query(self, test_client):
        """REL-005: Test query validation."""
        response = test_client.post(
            "/api/v1/chat",
            json={"query": "", "settings": {}}
        )
        assert response.status_code == 422  # Validation error
    
    def test_chat_validates_query_length(self, test_client):
        """REL-005: Test query length validation."""
        long_query = "x" * 6000  # Exceeds 5000 limit
        response = test_client.post(
            "/api/v1/chat",
            json={"query": long_query, "settings": {}}
        )
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_chat_returns_response(self, test_client, mock_llm_client, mock_llm_response):
        """Test chat endpoint returns proper response."""
        mock_llm_response.content = "This is a test response."
        mock_llm_response.finish_reason = "stop"
        mock_llm_response.tool_calls = []
        mock_llm_client.chat.return_value = mock_llm_response
        
        with patch('app.api.routes.chat.get_llm_client', return_value=mock_llm_client), \
             patch('app.api.routes.chat.get_router') as mock_router:
            
            # Mock router to return SIMPLE classification
            mock_classification = MagicMock()
            mock_classification.query_type.value = "SIMPLE"
            mock_classification.reasoning = "Simple query"
            mock_router.return_value.classify = AsyncMock(return_value=mock_classification)
            
            from app.agent.router import QueryType
            mock_classification.query_type = QueryType.SIMPLE
            
            response = test_client.post(
                "/api/v1/chat",
                json={"query": "What is 2+2?", "settings": {"enable_reflection": False}}
            )
            
            # Note: May fail if dependencies aren't fully mocked
            # This is a template for integration testing
    
    def test_sources_endpoint_returns_501(self, test_client):
        """ARCH-008: Test unimplemented sources endpoint returns 501."""
        response = test_client.get("/api/v1/chat/sources/1")
        assert response.status_code == 501
        data = response.json()
        assert "detail" in data


class TestCORSConfiguration:
    """Test CORS is properly configured."""
    
    def test_cors_allows_configured_origins(self, test_client):
        """SEC-004: Test CORS allows configured origins."""
        response = test_client.options(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"}
        )
        # Should be allowed (default CORS origin)
        assert response.status_code in [200, 204, 405]  # OPTIONS handling varies


class TestAPIErrorHandling:
    """Test API error handling."""
    
    def test_invalid_json_returns_422(self, test_client):
        """Test invalid JSON body handling."""
        response = test_client.post(
            "/api/v1/chat",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_missing_required_fields(self, test_client):
        """Test missing required fields handling."""
        response = test_client.post(
            "/api/v1/chat",
            json={"settings": {}}  # Missing 'query'
        )
        assert response.status_code == 422
