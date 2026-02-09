"""
Base LLM Client
===============

Abstract base class for LLM providers.
Defines the interface and shared data structures.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List, Optional, Any
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ChatResponse:
    """Response from chat completion."""
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    finish_reason: str = "stop"
    usage: Optional[Dict[str, int]] = None


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False
    ) -> ChatResponse:
        """Send chat request to LLM."""
        pass
    
    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> AsyncIterator[Dict]:
        """Stream chat response from LLM."""
        pass
