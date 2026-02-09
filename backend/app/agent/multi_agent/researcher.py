"""
Researcher Agent
================

Specialized agent for web research tasks.
Uses the existing ReACT agent to execute searches and gather information.

The Researcher:
1. Receives tasks from the Orchestrator
2. Executes web searches using ReACT
3. Collects and structures findings
4. Reports results back with sources
"""

import json
from typing import Dict, Any, Optional
import structlog

from app.agent.react import ReACTAgent
from app.agent.multi_agent.state import (
    AgentState,
    AgentRole,
    TaskStatus
)

logger = structlog.get_logger(__name__)


class ResearcherAgent:
    """Researcher agent for executing web research tasks.
    
    Wraps the ReACT agent to provide structured research capabilities
    within the multi-agent workflow.
    
    Example:
        researcher = ResearcherAgent()
        state = await researcher.research(state)
        # state.research_results now contains findings
    """
    
    def __init__(self, max_iterations: int = 3):
        """Initialize researcher.
        
        Args:
            max_iterations: Max ReACT iterations per task
        """
        self.max_iterations = max_iterations
        # PERF-001: Cache the ReACT agent instance
        self._react_agent: Optional[ReACTAgent] = None
    
    def _get_react_agent(self) -> ReACTAgent:
        """Get or create the cached ReACT agent."""
        if self._react_agent is None:
            self._react_agent = ReACTAgent(max_iterations=self.max_iterations)
        return self._react_agent
        
    async def research(self, state: AgentState) -> AgentState:
        """Execute all pending research tasks.
        
        Processes each pending subtask using the ReACT agent,
        collecting results and sources.
        
        Args:
            state: Current state with pending subtasks
            
        Returns:
            State with completed research results
        """
        pending_tasks = state.get_pending_tasks()
        
        if not pending_tasks:
            logger.warning("No pending tasks for researcher")
            return state
        
        logger.info(
            "Researcher starting",
            task_count=len(pending_tasks)
        )
        
        # Process each task
        for task in pending_tasks:
            await self._execute_task(state, task)
        
        # Log completion
        state.add_message(
            sender=AgentRole.RESEARCHER,
            receiver=AgentRole.SYNTHESIZER,
            content=json.dumps({
                "action": "research_complete",
                "results_count": len(state.research_results),
                "total_sources": len(state.sources)
            })
        )
        
        return state
    
    async def _execute_task(
        self,
        state: AgentState,
        task
    ) -> None:
        """Execute a single research task.
        
        Args:
            state: Current agent state
            task: SubTask to execute
        """
        logger.debug(f"Researching: {task.description[:50]}")
        task.status = TaskStatus.IN_PROGRESS
        
        try:
            # PERF-001: Use cached ReACT agent instance
            react = self._get_react_agent()
            result = await react.run(task.description)
            
            # Update task
            task.status = TaskStatus.COMPLETED
            task.result = result.answer
            task.sources = result.sources
            
            # Add to state
            state.add_research_result(
                task_id=task.id,
                answer=result.answer,
                sources=result.sources
            )
            
            logger.debug(
                f"Task {task.id} completed",
                sources=len(result.sources)
            )
            
        except Exception as e:
            logger.error(f"Research task failed: {e}")
            task.status = TaskStatus.FAILED
            task.result = f"Research failed: {str(e)}"
    
    async def research_single(
        self,
        query: str,
        state: AgentState
    ) -> Dict[str, Any]:
        """Execute a single research query.
        
        Convenience method for one-off research without subtasks.
        
        Args:
            query: Research question
            state: Current state (for adding results)
            
        Returns:
            Research result dict
        """
        # PERF-001: Use cached ReACT agent instance
        react = self._get_react_agent()
        result = await react.run(query)
        
        # Add to state
        state.add_research_result(
            task_id="adhoc",
            answer=result.answer,
            sources=result.sources
        )
        
        return {
            "answer": result.answer,
            "sources": result.sources
        }


# Factory function
_researcher: ResearcherAgent = None


def get_researcher() -> ResearcherAgent:
    """Get or create the researcher agent instance."""
    global _researcher
    if _researcher is None:
        _researcher = ResearcherAgent()
    return _researcher
