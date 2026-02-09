"""
Orchestrator Agent
==================

Central coordinator for multi-agent workflows.
Decomposes complex queries into subtasks and delegates to specialists.

The Orchestrator is responsible for:
1. Analyzing the query to understand its complexity
2. Breaking it down into focused subtasks
3. Assigning subtasks to appropriate worker agents
4. Coordinating the overall workflow
"""

import json
from typing import List, Dict, Any
import structlog

from app.llm.client import get_llm_client
from app.llm.prompts import get_prompt
from app.agent.multi_agent.state import (
    AgentState, 
    AgentRole, 
    SubTask,
    TaskStatus
)

logger = structlog.get_logger(__name__)


DECOMPOSITION_PROMPT = """You are an orchestrator agent. Your job is to decompose complex user queries into focused research subtasks.

Given a query, identify the key aspects that need to be researched separately. Each subtask should be:
- Focused on ONE specific aspect
- Searchable via web search
- Clear and specific

Respond with a JSON object containing a list of subtasks:
{
    "subtasks": [
        {"description": "Research subtask 1"},
        {"description": "Research subtask 2"},
        {"description": "Research subtask 3"}
    ],
    "reasoning": "Why you broke it down this way"
}

Keep subtasks to 3-5 maximum. If the query is simple, use just 1-2 subtasks.
"""


class OrchestratorAgent:
    """Orchestrator agent for task decomposition and coordination.
    
    The orchestrator analyzes the incoming query and creates a plan
    by decomposing it into subtasks that can be executed by specialist
    agents (researchers).
    
    Example:
        orchestrator = OrchestratorAgent()
        state = await orchestrator.plan(AgentState(query="Compare Tesla vs Rivian"))
        # state.subtasks now contains decomposed tasks
    """
    
    def __init__(self, max_subtasks: int = 5):
        """Initialize orchestrator.
        
        Args:
            max_subtasks: Maximum number of subtasks to create
        """
        self.llm = get_llm_client()
        self.max_subtasks = max_subtasks
        
    async def plan(self, state: AgentState) -> AgentState:
        """Decompose the query into subtasks.
        
        This is the main entry point for the orchestrator node.
        It analyzes the query and creates focused subtasks.
        
        Args:
            state: Current agent state with query
            
        Returns:
            Updated state with subtasks populated
        """
        logger.info("Orchestrator planning", query=state.query[:100])
        
        try:
            # Use LLM to decompose the query
            response = await self.llm.chat(
                messages=[
                    {"role": "system", "content": DECOMPOSITION_PROMPT},
                    {"role": "user", "content": f"Query: {state.query}"}
                ],
                temperature=0.3,
                max_tokens=1024
            )
            
            # Parse the response
            subtasks = self._parse_decomposition(response.content)
            
            # Add subtasks to state
            for task_desc in subtasks[:self.max_subtasks]:
                state.add_subtask(
                    description=task_desc,
                    assigned_to=AgentRole.RESEARCHER
                )
            
            # Log the plan
            state.add_message(
                sender=AgentRole.ORCHESTRATOR,
                receiver=AgentRole.RESEARCHER,
                content=json.dumps({
                    "action": "decomposed",
                    "subtasks": [t.description for t in state.subtasks]
                }),
                metadata={"subtask_count": len(state.subtasks)}
            )
            
            logger.info(
                "Orchestrator created plan",
                subtask_count=len(state.subtasks)
            )
            
        except Exception as e:
            logger.error(f"Orchestrator planning failed: {e}")
            # Fallback: treat the whole query as one task
            state.add_subtask(
                description=state.query,
                assigned_to=AgentRole.RESEARCHER
            )
            
        return state
    
    def _parse_decomposition(self, content: str) -> List[str]:
        """Parse LLM response to extract subtasks.
        
        Args:
            content: Raw LLM response
            
        Returns:
            List of subtask descriptions
        """
        try:
            # Try to parse as JSON
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            data = json.loads(content.strip())
            
            if isinstance(data, dict) and "subtasks" in data:
                return [t["description"] for t in data["subtasks"]]
            elif isinstance(data, list):
                return [t.get("description", str(t)) for t in data]
                
        except json.JSONDecodeError:
            logger.warning("Failed to parse decomposition as JSON")
        
        # Fallback: split by newlines/bullets
        lines = content.split("\n")
        subtasks = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith(("#", "{", "}", "[")):
                # Remove bullet points
                line = line.lstrip("-•*0123456789. ")
                if len(line) > 10:
                    subtasks.append(line)
        
        return subtasks if subtasks else [content[:500]]
    
    async def aggregate(self, state: AgentState) -> AgentState:
        """Aggregate research results (optional post-processing).
        
        This can be used as a separate node if the orchestrator
        needs to do final aggregation before synthesis.
        
        Args:
            state: State with completed research
            
        Returns:
            State with aggregated results
        """
        # Check if all tasks are complete
        pending = state.get_pending_tasks()
        if pending:
            logger.warning(
                "Aggregating with incomplete tasks",
                pending_count=len(pending)
            )
        
        # Log aggregation
        state.add_message(
            sender=AgentRole.ORCHESTRATOR,
            receiver=AgentRole.SYNTHESIZER,
            content=json.dumps({
                "action": "aggregate_complete",
                "research_count": len(state.research_results),
                "source_count": len(state.sources)
            })
        )
        
        return state


# Factory function for singleton-like access
_orchestrator: OrchestratorAgent = None


def get_orchestrator() -> OrchestratorAgent:
    """Get or create the orchestrator agent instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = OrchestratorAgent()
    return _orchestrator
