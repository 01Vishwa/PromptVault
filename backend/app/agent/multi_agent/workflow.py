"""
Workflow Definitions
====================

Pre-built multi-agent workflows for different use cases.

Provides factory functions to create configured WorkflowGraph
instances for common scenarios like research pipelines.
"""

import structlog

from app.agent.multi_agent.graph import WorkflowGraph
from app.agent.multi_agent.state import AgentState
from app.agent.multi_agent.orchestrator import get_orchestrator
from app.agent.multi_agent.researcher import get_researcher
from app.agent.multi_agent.synthesizer import get_synthesizer
from app.agent.multi_agent.critic import get_critic

logger = structlog.get_logger(__name__)


def build_research_workflow() -> WorkflowGraph:
    """Build the standard research pipeline workflow.
    
    This workflow implements the full multi-agent research pattern:
    
    ```
    start → orchestrator → researcher → synthesizer → critic
                                ↑                        ↓
                                └──────── (revise) ──────┘
                                          ↓
                                     finalize → end
    ```
    
    The critic can request revisions up to max_iterations times.
    
    Returns:
        Configured WorkflowGraph ready for execution
    """
    graph = WorkflowGraph()
    
    # Get agent instances
    orchestrator = get_orchestrator()
    researcher = get_researcher()
    synthesizer = get_synthesizer()
    critic = get_critic()
    
    # Add nodes
    graph.add_node("start", orchestrator.plan)
    graph.add_node("research", researcher.research)
    graph.add_node("synthesize", synthesizer.synthesize)
    graph.add_node("critique", critic.critique)
    graph.add_node("finalize", _finalize_node)
    
    # Add edges
    graph.add_edge("start", "research")
    graph.add_edge("research", "synthesize")
    graph.add_edge("synthesize", "critique")
    
    # Conditional edge from critic
    graph.add_conditional_edge("critique", critic.should_revise)
    
    # Finalize goes to end
    graph.add_edge("finalize", "end")
    
    logger.debug("Built research workflow")
    
    return graph


async def _finalize_node(state: AgentState) -> AgentState:
    """Finalize the workflow by setting final_answer.
    
    Copies the approved draft to final_answer and ensures
    sources are properly formatted.
    """
    if state.draft_answer:
        state.final_answer = state.draft_answer
    else:
        state.final_answer = "I was unable to generate an answer."
    
    logger.info(
        "Workflow finalized",
        answer_length=len(state.final_answer or ""),
        source_count=len(state.sources),
        iterations=state.iteration
    )
    
    return state


def build_quick_research_workflow() -> WorkflowGraph:
    """Build a simplified workflow without critique loop.
    
    ```
    start → orchestrator → researcher → synthesizer → finalize → end
    ```
    
    Faster execution without quality checks.
    
    Returns:
        Configured WorkflowGraph
    """
    graph = WorkflowGraph()
    
    orchestrator = get_orchestrator()
    researcher = get_researcher()
    synthesizer = get_synthesizer()
    
    graph.add_node("start", orchestrator.plan)
    graph.add_node("research", researcher.research)
    graph.add_node("synthesize", synthesizer.synthesize)
    graph.add_node("finalize", _finalize_node)
    
    graph.add_edge("start", "research")
    graph.add_edge("research", "synthesize")
    graph.add_edge("synthesize", "finalize")
    graph.add_edge("finalize", "end")
    
    return graph


async def run_research_pipeline(query: str) -> AgentState:
    """Convenience function to run the full research pipeline.
    
    Args:
        query: User's research question
        
    Returns:
        Completed AgentState with final_answer and sources
    """
    workflow = build_research_workflow()
    state = AgentState(query=query)
    
    logger.info("Starting research pipeline", query=query[:50])
    
    final_state = await workflow.run(state)
    
    return final_state


async def run_quick_research(query: str) -> AgentState:
    """Convenience function for quick research without critique.
    
    Args:
        query: User's question
        
    Returns:
        Completed AgentState
    """
    workflow = build_quick_research_workflow()
    state = AgentState(query=query)
    
    return await workflow.run(state)


# Export workflow builders
__all__ = [
    "build_research_workflow",
    "build_quick_research_workflow",
    "run_research_pipeline",
    "run_quick_research",
]
