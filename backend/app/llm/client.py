"""
Unified LLM Client
==================

Abstraction layer that provides automatic failover between
NVIDIA NIM (primary) and GitHub Models (fallback).

Ensures high availability and consistent interface regardless
of which provider is used.
"""

from typing import AsyncIterator, Dict, List, Optional, Any
from enum import Enum
import asyncio
import structlog

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.config import settings
from app.llm.base import ChatResponse, ToolCall
from app.llm.nvidia import NVIDIAClient, NVIDIAAPIError
from app.llm.github import GitHubModelsClient, GitHubModelsAPIError

logger = structlog.get_logger(__name__)

# REL-004: Retry configuration for transient failures
RETRY_CONFIG = {
    "stop": stop_after_attempt(3),
    "wait": wait_exponential(multiplier=1, min=1, max=10),
    "retry": retry_if_exception_type((NVIDIAAPIError, GitHubModelsAPIError, asyncio.TimeoutError)),
    "before_sleep": before_sleep_log(logger, log_level=20),  # INFO level
    "reraise": True
}


class Provider(str, Enum):
    """LLM Provider identifiers."""
    NVIDIA = "nvidia"
    GITHUB = "github"


class UnifiedLLMClient:
    """Unified interface for multiple LLM providers.
    
    Features:
    - Automatic failover from NVIDIA to GitHub on errors
    - Consistent interface regardless of provider
    - Provider preference configuration
    - Streaming and non-streaming support
    - Tool calling support
    
    Usage:
        client = UnifiedLLMClient()
        response = await client.chat([
            {"role": "user", "content": "Hello!"}
        ])
        print(response.content)
    """
    
    def __init__(
        self,
        prefer_provider: Provider = Provider.NVIDIA,
        enable_fallback: bool = True
    ):
        """Initialize unified client.
        
        Args:
            prefer_provider: Primary provider to use
            enable_fallback: Whether to fallback on primary failure
        """
        self.prefer_provider = prefer_provider
        self.enable_fallback = enable_fallback
        
        # Initialize provider clients
        self._nvidia = NVIDIAClient()
        self._github = GitHubModelsClient()
        
        # Track which provider was used for last request
        self.last_provider: Optional[Provider] = None
        
        logger.info(
            "Unified LLM client initialized",
            primary=prefer_provider.value,
            fallback_enabled=enable_fallback
        )
    
    def _get_primary_client(self):
        """Get the primary provider client."""
        if self.prefer_provider == Provider.NVIDIA:
            return self._nvidia
        return self._github
    
    def _get_fallback_client(self):
        """Get the fallback provider client."""
        if self.prefer_provider == Provider.NVIDIA:
            return self._github
        return self._nvidia
    
    @retry(**RETRY_CONFIG)
    async def _call_with_retry(
        self,
        client,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]],
        temperature: float,
        max_tokens: int,
        stream: bool
    ) -> ChatResponse:
        """Execute LLM call with retry logic for transient failures."""
        return await client.chat(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        force_provider: Optional[Provider] = None
    ) -> ChatResponse:
        """Send chat completion with automatic failover and retry.
        
        Args:
            messages: List of message dicts with role and content
            tools: Optional tool definitions (OpenAI format)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            stream: Whether to stream (returns collected response)
            force_provider: Force specific provider, skip failover
            
        Returns:
            ChatResponse with content and optional tool calls
        """
        # If forcing a specific provider (with retry)
        if force_provider:
            client = self._nvidia if force_provider == Provider.NVIDIA else self._github
            self.last_provider = force_provider
            return await self._call_with_retry(
                client, messages, tools, temperature, max_tokens, stream
            )
        
        # Try primary provider with retry
        primary = self._get_primary_client()
        primary_name = self.prefer_provider
        
        try:
            logger.debug(f"Trying {primary_name.value} provider")
            self.last_provider = primary_name
            return await self._call_with_retry(
                primary, messages, tools, temperature, max_tokens, stream
            )
        except (NVIDIAAPIError, GitHubModelsAPIError, Exception) as e:
            if not self.enable_fallback:
                raise
            
            logger.warning(
                f"{primary_name.value} failed after retries, falling back",
                error=str(e)
            )
        
        # Try fallback provider with retry
        fallback = self._get_fallback_client()
        fallback_name = Provider.GITHUB if primary_name == Provider.NVIDIA else Provider.NVIDIA
        
        logger.info(f"Using fallback provider: {fallback_name.value}")
        self.last_provider = fallback_name
        
        return await self._call_with_retry(
            fallback, messages, tools, temperature, max_tokens, stream
        )
    
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        force_provider: Optional[Provider] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream chat completion with automatic failover.
        
        Yields dicts with:
        - type: "content" | "tool_call" | "thinking" | "done"
        - data: chunk data
        - provider: which provider is being used
        """
        # Determine which provider to use
        if force_provider:
            client = self._nvidia if force_provider == Provider.NVIDIA else self._github
            self.last_provider = force_provider
        else:
            client = self._get_primary_client()
            self.last_provider = self.prefer_provider
        
        # Yield provider info
        yield {
            "type": "provider",
            "data": {"provider": self.last_provider.value}
        }
        
        try:
            async for chunk in client.stream_chat(
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                yield chunk
                
        except (NVIDIAAPIError, GitHubModelsAPIError, Exception) as e:
            if not self.enable_fallback or force_provider:
                yield {"type": "error", "data": {"error": str(e)}}
                return
            
            logger.warning(
                f"{self.last_provider.value} stream failed, falling back",
                error=str(e)
            )
            
            # Switch to fallback
            fallback = self._get_fallback_client()
            self.last_provider = (
                Provider.GITHUB 
                if self.prefer_provider == Provider.NVIDIA 
                else Provider.NVIDIA
            )
            
            yield {
                "type": "provider_switch",
                "data": {"provider": self.last_provider.value}
            }
            
            async for chunk in fallback.stream_chat(
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                yield chunk
    
    async def embed(
        self,
        texts: List[str],
        force_provider: Optional[Provider] = None
    ) -> List[List[float]]:
        """Generate embeddings with automatic failover.
        
        Args:
            texts: Texts to embed
            force_provider: Force specific provider
            
        Returns:
            List of embedding vectors
        """
        if force_provider:
            client = self._nvidia if force_provider == Provider.NVIDIA else self._github
            return await client.embed(texts)
        
        try:
            return await self._nvidia.embed(texts)
        except NVIDIAAPIError:
            if not self.enable_fallback:
                raise
            logger.warning("NVIDIA embeddings failed, using GitHub")
            return await self._github.embed(texts)
    
    async def close(self):
        """Close all provider clients."""
        await self._nvidia.close()
        await self._github.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Singleton instance for convenience
_client: Optional[UnifiedLLMClient] = None


def get_llm_client() -> UnifiedLLMClient:
    """Get or create the singleton LLM client.
    
    Returns:
        UnifiedLLMClient instance
    """
    global _client
    if _client is None:
        _client = UnifiedLLMClient()
    return _client


async def cleanup_llm_client():
    """Cleanup the singleton client on shutdown."""
    global _client
    if _client:
        await _client.close()
        _client = None
