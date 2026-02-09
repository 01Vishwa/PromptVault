"""
Response Models
===============

Pydantic models for API response serialization.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class StreamEventType(str, Enum):
    """Types of SSE stream events."""
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    CONTENT = "content"
    SOURCES = "sources"
    ERROR = "error"
    DONE = "done"


class Citation(BaseModel):
    """Source citation."""
    id: int = Field(..., description="Citation number [1], [2], etc.")
    title: str = Field(..., description="Source title")
    url: str = Field(..., description="Source URL")
    snippet: Optional[str] = Field(
        default=None,
        description="Relevant snippet from source"
    )
    domain: Optional[str] = Field(
        default=None,
        description="Domain of the source"
    )


class ThinkingData(BaseModel):
    """Agent thinking step data."""
    thought: str = Field(..., description="Agent's current thought")
    step: int = Field(default=1, description="Thinking step number")


class ToolCallData(BaseModel):
    """Tool call event data."""
    tool: str = Field(..., description="Tool name")
    args: Dict[str, Any] = Field(..., description="Tool arguments")


class ToolResultData(BaseModel):
    """Tool result event data."""
    tool: str = Field(..., description="Tool name")
    success: bool = Field(..., description="Whether tool succeeded")
    result: Optional[str] = Field(default=None, description="Tool result")
    sources: Optional[List[Citation]] = Field(
        default=None, 
        description="Sources from search"
    )


class ContentData(BaseModel):
    """Content chunk data."""
    delta: str = Field(..., description="Content chunk")


class DoneData(BaseModel):
    """Completion event data."""
    total_tokens: Optional[int] = Field(default=None, description="Tokens used")
    duration_ms: int = Field(..., description="Total duration in ms")
    sources_count: int = Field(default=0, description="Number of sources used")
    provider: str = Field(..., description="LLM provider used")


class StreamEvent(BaseModel):
    """Server-Sent Event for streaming."""
    type: StreamEventType
    data: Dict[str, Any]
    
    def to_sse(self) -> str:
        """Convert to SSE format string."""
        import json
        return f"data: {json.dumps({'type': self.type.value, 'data': self.data})}\n\n"


class ChatStartResponse(BaseModel):
    """Response when starting a chat job."""
    job_id: str = Field(..., description="Job ID for tracking")
    stream_url: str = Field(..., description="URL for SSE stream")
    status: str = Field(default="processing", description="Job status")


class ChatResponse(BaseModel):
    """Complete chat response (non-streaming)."""
    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="Generated answer")
    sources: List[Citation] = Field(
        default_factory=list,
        description="List of source citations"
    )
    thinking_steps: List[str] = Field(
        default_factory=list,
        description="Agent's thinking process"
    )
    tool_calls: List[str] = Field(
        default_factory=list,
        description="Tools used during processing"
    )
    duration_ms: int = Field(..., description="Processing time")
    provider: str = Field(..., description="LLM provider used")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "What is the capital of France?",
                    "answer": "The capital of France is **Paris**.",
                    "sources": [],
                    "thinking_steps": [],
                    "tool_calls": [],
                    "duration_ms": 245,
                    "provider": "nvidia"
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Error response."""
    error: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
