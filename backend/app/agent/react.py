"""
ReACT Agent
===========

Reasoning and Acting agent that uses a Thought-Action-Observation loop.
The core agentic pattern for multi-step reasoning with tool use.
"""

from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import json
import structlog

from app.llm.client import get_llm_client, ChatResponse
from app.llm.prompts import get_prompt
from app.tools.registry import get_registry, ToolRegistry
from app.config import settings

logger = structlog.get_logger(__name__)


class StepType(str, Enum):
    """Types of ReACT steps."""
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    ANSWER = "answer"


@dataclass
class ReACTStep:
    """A single step in the ReACT loop."""
    step_type: StepType
    content: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    sources: List[Dict] = field(default_factory=list)


@dataclass
class ReACTResult:
    """Result from ReACT agent execution."""
    answer: str
    steps: List[ReACTStep]
    sources: List[Dict]
    iterations: int
    success: bool
    error: Optional[str] = None


class ReACTAgent:
    """ReACT (Reasoning and Acting) Agent.
    
    Implements the classic ReACT loop:
    1. Thought: Reason about what to do next
    2. Action: Call a tool with specific arguments
    3. Observation: Receive tool results
    4. Repeat until answer is ready
    
    Features:
    - Multi-step reasoning with tools
    - Source citation collection
    - Iteration limit for safety
    - Streaming step output
    
    Example:
        agent = ReACTAgent()
        result = await agent.run("What are the latest AI developments?")
        print(result.answer)
        print(result.sources)
    """
    
    def __init__(
        self,
        max_iterations: int = None,
        tool_registry: ToolRegistry = None
    ):
        """Initialize ReACT agent.
        
        Args:
            max_iterations: Maximum T-A-O loops (defaults to config)
            tool_registry: Tool registry to use (defaults to global)
        """
        self.max_iterations = max_iterations or settings.max_react_iterations
        self.llm = get_llm_client()
        self.tools = tool_registry or get_registry()
        self.system_prompt = get_prompt("react")
    
    async def run(self, query: str) -> ReACTResult:
        """Execute ReACT loop for a query.
        
        Args:
            query: User's question
            
        Returns:
            ReACTResult with answer, steps, and sources
        """
        logger.info("Starting ReACT", query=query[:100])
        
        steps: List[ReACTStep] = []
        all_sources: List[Dict] = []
        
        # Build initial messages
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query}
        ]
        
        # Get tool schemas for LLM
        tool_schemas = self.tools.get_openai_tools()
        
        for iteration in range(self.max_iterations):
            logger.debug(f"ReACT iteration {iteration + 1}")
            
            try:
                # Get LLM response with tool calling
                response = await self.llm.chat(
                    messages=messages,
                    tools=tool_schemas,
                    temperature=0.7,
                    max_tokens=2048
                )
                
                # Check if we have a final answer
                if response.finish_reason == "stop" and not response.tool_calls:
                    # Final answer reached
                    answer = response.content
                    
                    steps.append(ReACTStep(
                        step_type=StepType.ANSWER,
                        content=answer
                    ))
                    
                    logger.info(
                        "ReACT complete",
                        iterations=iteration + 1,
                        sources=len(all_sources)
                    )
                    
                    return ReACTResult(
                        answer=answer,
                        steps=steps,
                        sources=all_sources,
                        iterations=iteration + 1,
                        success=True
                    )
                
                # Process tool calls
                if response.tool_calls:
                    # Add assistant message with tool calls
                    tool_call_msg = {
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments)
                                }
                            }
                            for tc in response.tool_calls
                        ]
                    }
                    messages.append(tool_call_msg)
                    
                    # Record thought if present
                    if response.content:
                        steps.append(ReACTStep(
                            step_type=StepType.THOUGHT,
                            content=response.content
                        ))
                    
                    # Execute each tool call
                    for tool_call in response.tool_calls:
                        # Record action
                        steps.append(ReACTStep(
                            step_type=StepType.ACTION,
                            content=f"Calling {tool_call.name}",
                            tool_name=tool_call.name,
                            tool_args=tool_call.arguments
                        ))
                        
                        # Execute tool
                        result = await self.tools.execute(
                            tool_call.name,
                            **tool_call.arguments
                        )
                        
                        # Collect sources
                        if result.sources:
                            all_sources.extend(result.sources)
                        
                        # Record observation
                        observation = result.to_observation()
                        steps.append(ReACTStep(
                            step_type=StepType.OBSERVATION,
                            content=observation[:settings.observation_truncate_length],  # Use config value
                            sources=result.sources
                        ))
                        
                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": observation
                        })
                
                else:
                    # No tool calls and no stop - add content and continue
                    if response.content:
                        steps.append(ReACTStep(
                            step_type=StepType.THOUGHT,
                            content=response.content
                        ))
                        messages.append({
                            "role": "assistant",
                            "content": response.content
                        })
                
            except Exception as e:
                logger.error(f"ReACT iteration error: {e}")
                return ReACTResult(
                    answer="",
                    steps=steps,
                    sources=all_sources,
                    iterations=iteration + 1,
                    success=False,
                    error=str(e)
                )
        
        # Max iterations reached - synthesize from what we have
        logger.warning("ReACT max iterations reached")
        
        # Ask LLM to synthesize final answer
        messages.append({
            "role": "user",
            "content": "Please provide your final answer based on the information gathered."
        })
        
        try:
            response = await self.llm.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )
            
            return ReACTResult(
                answer=response.content,
                steps=steps,
                sources=all_sources,
                iterations=self.max_iterations,
                success=True
            )
        except Exception as e:
            return ReACTResult(
                answer="Unable to complete analysis within iteration limit.",
                steps=steps,
                sources=all_sources,
                iterations=self.max_iterations,
                success=False,
                error=str(e)
            )
    
    async def stream(self, query: str) -> AsyncIterator[Dict[str, Any]]:
        """Stream ReACT execution steps.
        
        Yields events for each step in the loop:
        - {"type": "thought", "content": "..."}
        - {"type": "action", "tool": "...", "args": {...}}
        - {"type": "observation", "content": "...", "sources": [...]}
        - {"type": "answer", "content": "...", "sources": [...]}
        """
        logger.info("Starting ReACT stream", query=query[:100])
        
        all_sources: List[Dict] = []
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query}
        ]
        
        tool_schemas = self.tools.get_openai_tools()
        
        for iteration in range(self.max_iterations):
            yield {
                "type": "iteration",
                "data": {"iteration": iteration + 1, "max": self.max_iterations}
            }
            
            try:
                response = await self.llm.chat(
                    messages=messages,
                    tools=tool_schemas,
                    temperature=0.7
                )
                
                # Final answer
                if response.finish_reason == "stop" and not response.tool_calls:
                    yield {
                        "type": "answer",
                        "data": {
                            "content": response.content,
                            "sources": all_sources
                        }
                    }
                    return
                
                # Thought
                if response.content:
                    yield {
                        "type": "thought",
                        "data": {"content": response.content}
                    }
                
                # Tool calls
                if response.tool_calls:
                    tool_call_msg = {
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments)
                                }
                            }
                            for tc in response.tool_calls
                        ]
                    }
                    messages.append(tool_call_msg)
                    
                    for tool_call in response.tool_calls:
                        yield {
                            "type": "action",
                            "data": {
                                "tool": tool_call.name,
                                "args": tool_call.arguments
                            }
                        }
                        
                        result = await self.tools.execute(
                            tool_call.name,
                            **tool_call.arguments
                        )
                        
                        if result.sources:
                            all_sources.extend(result.sources)
                        
                        yield {
                            "type": "observation",
                            "data": {
                                "content": result.to_observation()[:500],
                                "sources": result.sources,
                                "success": result.success
                            }
                        }
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result.to_observation()
                        })
                
            except Exception as e:
                yield {
                    "type": "error",
                    "data": {"error": str(e)}
                }
                return
        
        # Max iterations
        yield {
            "type": "max_iterations",
            "data": {"iterations": self.max_iterations}
        }


# Singleton
_agent: Optional[ReACTAgent] = None


def get_react_agent() -> ReACTAgent:
    """Get or create singleton ReACT agent."""
    global _agent
    if _agent is None:
        _agent = ReACTAgent()
    return _agent
