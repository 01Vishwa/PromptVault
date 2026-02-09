"""
Agent Tests
===========

Tests for the agent system (ReACT, Router, Reflexion).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestQueryRouter:
    """Test QueryRouter classification."""
    
    @pytest.mark.asyncio
    async def test_classify_simple_query(self, mock_llm_client):
        """Test classification of simple queries."""
        mock_llm_client.chat.return_value.content = "SIMPLE - This is a basic question."
        
        with patch('app.agent.router.get_llm_client', return_value=mock_llm_client):
            from app.agent.router import QueryRouter, QueryType
            
            router = QueryRouter()
            router.llm = mock_llm_client
            result = await router.classify("What is 2+2?")
            
            assert result.query_type == QueryType.SIMPLE
    
    @pytest.mark.asyncio
    async def test_classify_research_query(self, mock_llm_client):
        """Test classification of research queries."""
        mock_llm_client.chat.return_value.content = "RESEARCH - Requires multiple searches."
        
        with patch('app.agent.router.get_llm_client', return_value=mock_llm_client):
            from app.agent.router import QueryRouter, QueryType
            
            router = QueryRouter()
            router.llm = mock_llm_client
            result = await router.classify("Compare Tesla and Rivian sales")
            
            assert result.query_type == QueryType.RESEARCH
    
    @pytest.mark.asyncio
    async def test_classify_fallback_on_error(self, mock_llm_client):
        """REL-007: Test fallback to RESEARCH on classification error."""
        mock_llm_client.chat.side_effect = Exception("API Error")
        
        with patch('app.agent.router.get_llm_client', return_value=mock_llm_client):
            from app.agent.router import QueryRouter, QueryType
            
            router = QueryRouter()
            router.llm = mock_llm_client
            result = await router.classify("Any query")
            
            assert result.query_type == QueryType.RESEARCH
            assert result.confidence == 0.5


class TestReACTAgent:
    """Test ReACT agent."""
    
    @pytest.mark.asyncio
    async def test_react_returns_answer_without_tools(self, mock_llm_client, mock_llm_response):
        """Test ReACT returns answer when no tools needed."""
        mock_llm_response.finish_reason = "stop"
        mock_llm_response.tool_calls = []
        mock_llm_response.content = "The answer is 4."
        mock_llm_client.chat.return_value = mock_llm_response
        
        with patch('app.agent.react.get_llm_client', return_value=mock_llm_client):
            with patch('app.agent.react.get_registry') as mock_registry:
                mock_registry.return_value.get_openai_tools.return_value = []
                
                from app.agent.react import ReACTAgent
                
                agent = ReACTAgent(max_iterations=3)
                agent.llm = mock_llm_client
                result = await agent.run("What is 2+2?")
                
                assert result.success is True
                assert result.answer == "The answer is 4."
                assert result.iterations == 1
    
    @pytest.mark.asyncio
    async def test_react_max_iterations_returns_success(self, mock_llm_client, mock_llm_response):
        """REL-008: Test max iterations still returns something useful."""
        # Simulate tool call response that never finishes
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.name = "web_search"
        mock_tool_call.arguments = {"query": "test"}
        
        mock_llm_response.finish_reason = "tool_calls"
        mock_llm_response.tool_calls = [mock_tool_call]
        mock_llm_response.content = "Let me search..."
        mock_llm_client.chat.return_value = mock_llm_response
        
        # After max iterations, return final answer
        final_response = MagicMock()
        final_response.content = "Final synthesized answer"
        final_response.finish_reason = "stop"
        final_response.tool_calls = []
        
        # Return tool calls for iterations, then final answer
        mock_llm_client.chat.side_effect = [
            mock_llm_response,  # First iteration with tool call
            final_response      # Synthesis call
        ]
        
        with patch('app.agent.react.get_llm_client', return_value=mock_llm_client):
            with patch('app.agent.react.get_registry') as mock_registry:
                mock_reg = MagicMock()
                mock_reg.get_openai_tools.return_value = []
                mock_reg.execute = AsyncMock(return_value=MagicMock(
                    success=True,
                    to_observation=MagicMock(return_value="Search results..."),
                    sources=[]
                ))
                mock_registry.return_value = mock_reg
                
                from app.agent.react import ReACTAgent
                
                agent = ReACTAgent(max_iterations=1)
                agent.llm = mock_llm_client
                agent.tools = mock_reg
                
                result = await agent.run("Complex query")
                
                # Should succeed even after max iterations
                assert result.success is True


class TestReflexion:
    """Test Reflexion module."""
    
    @pytest.mark.asyncio
    async def test_reflexion_returns_failing_on_error(self, mock_llm_client):
        """REL-001: Test Reflexion returns failing critique on error."""
        mock_llm_client.chat.side_effect = Exception("API Error")
        
        with patch('app.agent.reflection.get_llm_client', return_value=mock_llm_client):
            from app.agent.reflection import ReflexionModule
            
            module = ReflexionModule(threshold=7.0)
            module.llm = mock_llm_client
            
            result = await module.evaluate(
                query="Test query",
                response="Test response"
            )
            
            # Should NOT pass when there's an error
            assert result.passed is False
            assert result.overall_score == 0.0
            assert len(result.issues) > 0
    
    @pytest.mark.asyncio
    async def test_reflexion_passes_good_response(self, mock_llm_client, mock_llm_response):
        """Test Reflexion passes responses above threshold."""
        mock_llm_response.content = """
        Accuracy: 9
        Completeness: 8
        Citations: 8
        Clarity: 9
        Overall: 8.5
        
        Issues:
        - Minor formatting issue
        
        Suggestions:
        - Could add more examples
        """
        mock_llm_client.chat.return_value = mock_llm_response
        
        with patch('app.agent.reflection.get_llm_client', return_value=mock_llm_client):
            from app.agent.reflection import ReflexionModule
            
            module = ReflexionModule(threshold=7.0)
            module.llm = mock_llm_client
            
            result = await module.evaluate(
                query="Test query",
                response="Test response"
            )
            
            assert result.passed is True
            assert result.overall_score >= 7.0
