"""
Agent State
===========

Shared state management for multi-agent workflows.
Implements LangGraph-style state passing without external databases.

The AgentState is passed through the workflow graph, accumulating
messages, research results, and drafts as agents process the query.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import uuid


class AgentRole(str, Enum):
    """Roles in the multi-agent system."""
    ORCHESTRATOR = "orchestrator"
    RESEARCHER = "researcher"
    SYNTHESIZER = "synthesizer"
    CRITIC = "critic"


class TaskStatus(str, Enum):
    """Status of a delegated task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Message:
    """Inter-agent message for coordination.
    
    Messages are the primary mechanism for agents to communicate.
    Each message has a sender, receiver, content, and optional metadata.
    
    Attributes:
        id: Unique message identifier
        sender: Role of the sending agent
        receiver: Role of the receiving agent
        content: Message content (can be JSON string for structured data)
        metadata: Additional context (timestamps, task IDs, etc.)
        created_at: Message creation timestamp
    """
    sender: AgentRole
    receiver: AgentRole
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "sender": self.sender.value,
            "receiver": self.receiver.value,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at
        }


@dataclass
class SubTask:
    """A decomposed subtask from the orchestrator.
    
    Attributes:
        id: Unique task identifier
        description: What needs to be done
        assigned_to: Which agent handles this
        status: Current task status
        result: Task output when completed
    """
    id: str
    description: str
    assigned_to: AgentRole
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    sources: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert subtask to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "assigned_to": self.assigned_to.value,
            "status": self.status.value,
            "result": self.result,
            "sources": self.sources
        }


@dataclass
class AgentState:
    """Shared state passed through the workflow graph.
    
    This is the core data structure that flows through the multi-agent
    system. Each agent reads from and writes to this state.
    
    The state follows LangGraph conventions:
    - Mutable pattern: agents modify state in-place for efficiency
    - Accumulative: lists grow as agents add data
    - Traceable: all changes are recorded via messages
    
    Attributes:
        query: Original user query
        messages: Inter-agent communication log
        subtasks: Decomposed tasks from orchestrator
        research_results: Findings from researcher agents
        sources: Collected source citations
        draft_answer: Current answer draft
        critique: Feedback from critic agent
        final_answer: Approved final response
        current_node: Current position in workflow graph
        iteration: Loop counter for revision cycles
        max_iterations: Maximum allowed revision cycles
        error: Error message if workflow fails
    """
    # Input
    query: str
    
    # Communication
    messages: List[Message] = field(default_factory=list)
    subtasks: List[SubTask] = field(default_factory=list)
    
    # Research outputs
    research_results: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    
    # Answer generation
    draft_answer: Optional[str] = None
    critique: Optional[Dict[str, Any]] = None
    final_answer: Optional[str] = None
    
    # Workflow control
    current_node: str = "start"
    iteration: int = 0
    max_iterations: int = 3
    
    # Error handling
    error: Optional[str] = None
    
    def add_message(
        self,
        sender: AgentRole,
        receiver: AgentRole,
        content: str,
        metadata: Optional[Dict] = None
    ) -> "AgentState":
        """Add a message to the state.
        
        Mutates the current state in-place and returns self for chaining.
        This is a mutable operation for efficiency in the workflow graph.
        """
        message = Message(
            sender=sender,
            receiver=receiver,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        return self
    
    def add_subtask(
        self,
        description: str,
        assigned_to: AgentRole = AgentRole.RESEARCHER
    ) -> SubTask:
        """Create and add a subtask.
        
        Returns the created subtask for reference.
        """
        subtask = SubTask(
            id=f"task_{len(self.subtasks) + 1}",
            description=description,
            assigned_to=assigned_to
        )
        self.subtasks.append(subtask)
        return subtask
    
    def get_pending_tasks(self) -> List[SubTask]:
        """Get all pending subtasks."""
        return [t for t in self.subtasks if t.status == TaskStatus.PENDING]
    
    def add_research_result(
        self,
        task_id: str,
        answer: str,
        sources: List[Dict]
    ) -> None:
        """Record research result and update sources."""
        self.research_results.append({
            "task_id": task_id,
            "answer": answer,
            "sources": sources
        })
        
        # Deduplicate and add sources
        existing_urls = {s.get("url") for s in self.sources}
        for source in sources:
            if source.get("url") not in existing_urls:
                self.sources.append(source)
                existing_urls.add(source.get("url"))
    
    def should_continue(self) -> bool:
        """Check if workflow should continue iterating."""
        return self.iteration < self.max_iterations and not self.error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "query": self.query,
            "messages": [m.to_dict() for m in self.messages],
            "subtasks": [t.to_dict() for t in self.subtasks],
            "research_results": self.research_results,
            "sources": self.sources,
            "draft_answer": self.draft_answer,
            "critique": self.critique,
            "final_answer": self.final_answer,
            "current_node": self.current_node,
            "iteration": self.iteration,
            "error": self.error
        }
