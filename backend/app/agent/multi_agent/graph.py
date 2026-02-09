"""
Workflow Graph
==============

LangGraph-style graph executor for multi-agent workflows.
Implements node-based execution with conditional routing.

This is a lightweight implementation that mimics LangGraph concepts
without requiring the LangGraph library or external databases.
"""

from typing import Callable, Dict, Optional, Any, Union, Awaitable
from dataclasses import dataclass, field
import structlog
import asyncio

from app.agent.multi_agent.state import AgentState

logger = structlog.get_logger(__name__)


# Type aliases
NodeFunction = Callable[[AgentState], Awaitable[AgentState]]
RouterFunction = Callable[[AgentState], str]


@dataclass
class NodeResult:
    """Result from executing a node."""
    state: AgentState
    next_node: Optional[str] = None
    error: Optional[str] = None


class WorkflowGraph:
    """Simple graph executor mimicking LangGraph patterns.
    
    The graph consists of:
    - Nodes: Async functions that transform state
    - Edges: Static transitions between nodes
    - Conditional Edges: Dynamic routing based on state
    
    Execution starts at "start" and ends at "end".
    
    Example:
        graph = WorkflowGraph()
        graph.add_node("start", orchestrator.plan)
        graph.add_node("research", researcher.research)
        graph.add_edge("start", "research")
        graph.add_edge("research", "end")
        
        final_state = await graph.run(AgentState(query="..."))
    
    Attributes:
        nodes: Mapping of node names to handler functions
        edges: Static node transitions
        conditional_edges: Dynamic routing functions
        entry_point: Starting node (default: "start")
    """
    
    def __init__(self):
        """Initialize empty workflow graph."""
        self.nodes: Dict[str, NodeFunction] = {}
        self.edges: Dict[str, str] = {}
        self.conditional_edges: Dict[str, RouterFunction] = {}
        self.entry_point: str = "start"
        
    def add_node(self, name: str, fn: NodeFunction) -> "WorkflowGraph":
        """Add a node to the graph.
        
        Args:
            name: Unique node identifier
            fn: Async function that takes and returns AgentState
            
        Returns:
            Self for method chaining
        """
        if name in self.nodes:
            logger.warning(f"Overwriting existing node: {name}")
        self.nodes[name] = fn
        logger.debug(f"Added node: {name}")
        return self
    
    def add_edge(self, from_node: str, to_node: str) -> "WorkflowGraph":
        """Add a static edge between nodes.
        
        Args:
            from_node: Source node name
            to_node: Destination node name
            
        Returns:
            Self for method chaining
        """
        self.edges[from_node] = to_node
        logger.debug(f"Added edge: {from_node} -> {to_node}")
        return self
    
    def add_conditional_edge(
        self,
        from_node: str,
        router: RouterFunction
    ) -> "WorkflowGraph":
        """Add a conditional edge with dynamic routing.
        
        The router function receives the current state and returns
        the name of the next node to execute.
        
        Args:
            from_node: Source node name
            router: Function that takes state and returns next node name
            
        Returns:
            Self for method chaining
        """
        self.conditional_edges[from_node] = router
        logger.debug(f"Added conditional edge from: {from_node}")
        return self
    
    def set_entry_point(self, node: str) -> "WorkflowGraph":
        """Set the starting node for execution.
        
        Args:
            node: Name of the entry node
            
        Returns:
            Self for method chaining
        """
        self.entry_point = node
        return self
    
    async def run(
        self,
        state: AgentState,
        max_steps: int = 20
    ) -> AgentState:
        """Execute the workflow graph.
        
        Starts at the entry point and continues until reaching "end"
        or hitting the max_steps limit.
        
        Args:
            state: Initial agent state
            max_steps: Maximum execution steps (prevents infinite loops)
            
        Returns:
            Final agent state after workflow completion
        """
        current = self.entry_point
        step = 0
        
        logger.info(
            "Starting workflow execution",
            entry_point=current,
            query=state.query[:50]
        )
        
        while current != "end" and step < max_steps:
            step += 1
            state.current_node = current
            
            # Execute current node if it exists
            if current in self.nodes:
                try:
                    logger.debug(f"Executing node: {current}", step=step)
                    state = await self.nodes[current](state)
                except Exception as e:
                    logger.error(f"Node {current} failed: {e}")
                    state.error = f"Node '{current}' failed: {str(e)}"
                    break
            
            # Determine next node
            if current in self.conditional_edges:
                # Dynamic routing
                router = self.conditional_edges[current]
                try:
                    next_node = router(state)
                    logger.debug(f"Router chose: {next_node}")
                except Exception as e:
                    logger.error(f"Router failed: {e}")
                    state.error = f"Routing failed: {str(e)}"
                    break
            elif current in self.edges:
                # Static transition
                next_node = self.edges[current]
            else:
                # No outgoing edge, end execution
                logger.warning(f"No edge from node: {current}")
                break
            
            current = next_node
        
        if step >= max_steps:
            logger.warning("Workflow hit max steps limit", max_steps=max_steps)
            state.error = f"Workflow exceeded {max_steps} steps"
        
        logger.info(
            "Workflow completed",
            steps=step,
            final_node=current,
            has_error=bool(state.error)
        )
        
        return state
    
    async def run_streaming(
        self,
        state: AgentState,
        max_steps: int = 20
    ):
        """Execute workflow and yield state after each node.
        
        Useful for streaming progress to clients.
        
        Args:
            state: Initial agent state
            max_steps: Maximum execution steps
            
        Yields:
            AgentState after each node execution
        """
        current = self.entry_point
        step = 0
        
        while current != "end" and step < max_steps:
            step += 1
            state.current_node = current
            
            if current in self.nodes:
                try:
                    state = await self.nodes[current](state)
                    yield state
                except Exception as e:
                    state.error = f"Node '{current}' failed: {str(e)}"
                    yield state
                    break
            
            # Determine next node (same logic as run)
            if current in self.conditional_edges:
                next_node = self.conditional_edges[current](state)
            elif current in self.edges:
                next_node = self.edges[current]
            else:
                break
            
            current = next_node


def create_passthrough_node(
    update_fn: Callable[[AgentState], None]
) -> NodeFunction:
    """Create a node that updates state in-place.
    
    Useful for simple state modifications without full node logic.
    
    Args:
        update_fn: Sync function that modifies state in-place
        
    Returns:
        Async node function
    """
    async def node(state: AgentState) -> AgentState:
        update_fn(state)
        return state
    return node
