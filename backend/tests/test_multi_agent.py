"""
Multi-Agent Tests
=================

Tests for the multi-agent system (Orchestrator, Researcher, Synthesizer, Critic).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAgentState:
    """Test AgentState class."""
    
    def test_state_initialization(self):
        """Test state initializes correctly."""
        from app.agent.multi_agent.state import AgentState
        
        state = AgentState(query="Test query")
        
        assert state.query == "Test query"
        assert state.messages == []
        assert state.subtasks == []
        assert state.iteration == 0
        assert state.should_continue() is True
    
    def test_add_message(self):
        """Test adding messages to state."""
        from app.agent.multi_agent.state import AgentState, AgentRole
        
        state = AgentState(query="Test")
        state.add_message(
            sender=AgentRole.ORCHESTRATOR,
            receiver=AgentRole.RESEARCHER,
            content="Do research"
        )
        
        assert len(state.messages) == 1
        assert state.messages[0].sender == AgentRole.ORCHESTRATOR
    
    def test_add_subtask(self):
        """Test adding subtasks."""
        from app.agent.multi_agent.state import AgentState, AgentRole
        
        state = AgentState(query="Test")
        task = state.add_subtask("Research AI", AgentRole.RESEARCHER)
        
        assert len(state.subtasks) == 1
        assert task.description == "Research AI"
        assert task.id == "task_1"
    
    def test_should_continue_respects_max_iterations(self):
        """Test iteration limit."""
        from app.agent.multi_agent.state import AgentState
        
        state = AgentState(query="Test", max_iterations=2)
        state.iteration = 2
        
        assert state.should_continue() is False
    
    def test_should_continue_respects_error(self):
        """Test error stops continuation."""
        from app.agent.multi_agent.state import AgentState
        
        state = AgentState(query="Test")
        state.error = "Something went wrong"
        
        assert state.should_continue() is False


class TestCriticAgent:
    """Test CriticAgent."""
    
    @pytest.mark.asyncio
    async def test_critic_returns_revise_on_error(self, mock_llm_client):
        """REL-002: Test critic returns REVISE on error."""
        mock_llm_client.chat.side_effect = Exception("API Error")
        
        with patch('app.agent.multi_agent.critic.get_llm_client', return_value=mock_llm_client):
            from app.agent.multi_agent.critic import CriticAgent
            from app.agent.multi_agent.state import AgentState
            
            critic = CriticAgent(threshold=7.0)
            critic.llm = mock_llm_client
            
            state = AgentState(query="Test query")
            state.draft_answer = "Test answer"
            
            result_state = await critic.critique(state)
            
            # Should NOT approve when there's an error
            assert result_state.critique["verdict"] == "REVISE"
            assert result_state.critique["overall_score"] == 0.0
    
    @pytest.mark.asyncio
    async def test_critic_approves_good_answer(self, mock_llm_client, mock_llm_response):
        """Test critic approves good answers."""
        mock_llm_response.content = '''```json
{
    "scores": {"accuracy": 9, "completeness": 8, "citations": 8, "clarity": 9},
    "overall_score": 8.5,
    "verdict": "APPROVE",
    "issues": [],
    "suggestions": []
}
```'''
        mock_llm_client.chat.return_value = mock_llm_response
        
        with patch('app.agent.multi_agent.critic.get_llm_client', return_value=mock_llm_client):
            from app.agent.multi_agent.critic import CriticAgent
            from app.agent.multi_agent.state import AgentState
            
            critic = CriticAgent(threshold=7.0)
            critic.llm = mock_llm_client
            
            state = AgentState(query="Test query")
            state.draft_answer = "A well-researched answer with citations [1]."
            state.sources = [{"title": "Source", "url": "https://example.com"}]
            
            result_state = await critic.critique(state)
            
            assert result_state.critique["verdict"] == "APPROVE"
    
    def test_should_revise_returns_finalize_on_approve(self):
        """Test routing logic on approval."""
        from app.agent.multi_agent.critic import CriticAgent
        from app.agent.multi_agent.state import AgentState
        
        critic = CriticAgent()
        state = AgentState(query="Test")
        state.critique = {"verdict": "APPROVE", "overall_score": 8.0}
        
        next_node = critic.should_revise(state)
        
        assert next_node == "finalize"
    
    def test_should_revise_respects_max_iterations(self):
        """Test max iterations forces finalize."""
        from app.agent.multi_agent.critic import CriticAgent
        from app.agent.multi_agent.state import AgentState
        
        critic = CriticAgent()
        state = AgentState(query="Test", max_iterations=2)
        state.iteration = 3  # Beyond max
        state.critique = {"verdict": "REVISE", "overall_score": 5.0}
        
        next_node = critic.should_revise(state)
        
        assert next_node == "finalize"


class TestSynthesizerAgent:
    """Test SynthesizerAgent."""
    
    @pytest.mark.asyncio
    async def test_synthesizer_handles_empty_results(self, mock_llm_client):
        """Test synthesizer handles no research results."""
        with patch('app.agent.multi_agent.synthesizer.get_llm_client', return_value=mock_llm_client):
            from app.agent.multi_agent.synthesizer import SynthesizerAgent
            from app.agent.multi_agent.state import AgentState
            
            synthesizer = SynthesizerAgent()
            state = AgentState(query="Test query")
            # No research_results
            
            result_state = await synthesizer.synthesize(state)
            
            assert result_state.draft_answer is not None
            assert "couldn't find" in result_state.draft_answer.lower()
    
    @pytest.mark.asyncio
    async def test_synthesizer_fallback_on_error(self, mock_llm_client):
        """AI-001: Test fallback synthesis on LLM error."""
        mock_llm_client.chat.side_effect = Exception("API Error")
        
        with patch('app.agent.multi_agent.synthesizer.get_llm_client', return_value=mock_llm_client):
            from app.agent.multi_agent.synthesizer import SynthesizerAgent
            from app.agent.multi_agent.state import AgentState
            
            synthesizer = SynthesizerAgent()
            synthesizer.llm = mock_llm_client
            
            state = AgentState(query="Test query")
            state.research_results = [
                {"task_id": "task_1", "answer": "Finding 1", "sources": []}
            ]
            
            result_state = await synthesizer.synthesize(state)
            
            # Should still produce an answer via fallback
            assert result_state.draft_answer is not None
            assert "Finding 1" in result_state.draft_answer


class TestResearcherAgent:
    """Test ResearcherAgent."""
    
    @pytest.mark.asyncio
    async def test_researcher_handles_task_failure(self, mock_llm_client):
        """Test researcher handles task failures gracefully."""
        with patch('app.agent.react.get_llm_client', return_value=mock_llm_client):
            mock_llm_client.chat.side_effect = Exception("API Error")
            
            from app.agent.multi_agent.researcher import ResearcherAgent
            from app.agent.multi_agent.state import AgentState, AgentRole, TaskStatus
            
            researcher = ResearcherAgent(max_iterations=1)
            
            state = AgentState(query="Test query")
            task = state.add_subtask("Research something", AgentRole.RESEARCHER)
            
            result_state = await researcher.research(state)
            
            # Task should be marked as failed
            assert task.status == TaskStatus.FAILED
            assert "failed" in task.result.lower()
