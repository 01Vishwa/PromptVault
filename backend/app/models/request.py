"""
Request Models
==============

Pydantic models for API request validation.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SearchDepth(str, Enum):
    """Search depth levels."""
    QUICK = "quick"
    NORMAL = "normal"
    DEEP = "deep"


class ChatSettings(BaseModel):
    """Settings for chat request."""
    model: Optional[str] = Field(
        default=None,
        description="Model to use (defaults to server config)"
    )
    search_depth: SearchDepth = Field(
        default=SearchDepth.NORMAL,
        description="Depth of web search"
    )
    max_sources: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of sources to return"
    )
    enable_reflection: bool = Field(
        default=True,
        description="Enable self-correction via Reflexion"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature"
    )


class ChatRequest(BaseModel):
    """Chat request body."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The user's question or query"
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="ID to continue existing conversation"
    )
    settings: ChatSettings = Field(
        default_factory=ChatSettings,
        description="Chat settings"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "Compare NVIDIA and AMD GPU performance in 2024",
                    "settings": {
                        "search_depth": "deep",
                        "max_sources": 10
                    }
                }
            ]
        }
    }


class Message(BaseModel):
    """Chat message."""
    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")


class HistoryRequest(BaseModel):
    """Request for conversation history."""
    conversation_id: str = Field(..., description="Conversation ID")
    limit: int = Field(default=50, ge=1, le=100, description="Max messages")
