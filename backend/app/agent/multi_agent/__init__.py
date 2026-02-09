"""
Multi-Agent System
==================

LangGraph-style orchestration for complex queries.
Implements Orchestrator-Worker pattern with:
- OrchestratorAgent: Task decomposition and delegation
- ResearcherAgent: Web research specialist
- SynthesizerAgent: Report/answer composition
- CriticAgent: Quality assurance and fact-checking
"""

from app.agent.multi_agent.state import AgentState, Message, AgentRole, SubTask, TaskStatus
from app.agent.multi_agent.graph import WorkflowGraph
from app.agent.multi_agent.orchestrator import OrchestratorAgent, get_orchestrator
from app.agent.multi_agent.researcher import ResearcherAgent, get_researcher
from app.agent.multi_agent.synthesizer import SynthesizerAgent, get_synthesizer
from app.agent.multi_agent.critic import CriticAgent, get_critic
from app.agent.multi_agent.workflow import (
    build_research_workflow,
    build_quick_research_workflow,
    run_research_pipeline,
    run_quick_research,
)

__all__ = [
    # State management
    "AgentState",
    "Message", 
    "AgentRole",
    "SubTask",
    "TaskStatus",
    # Graph
    "WorkflowGraph",
    # Agents
    "OrchestratorAgent",
    "ResearcherAgent",
    "SynthesizerAgent",
    "CriticAgent",
    # Factory functions
    "get_orchestrator",
    "get_researcher",
    "get_synthesizer",
    "get_critic",
    # Workflows
    "build_research_workflow",
    "build_quick_research_workflow",
    "run_research_pipeline",
    "run_quick_research",
]
