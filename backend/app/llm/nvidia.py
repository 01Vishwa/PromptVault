"""
NVIDIA NIM Client
================

Integration with NVIDIA NIM API for Nemotron and NeMo models.
Primary LLM provider for Axiom AI.
"""

import json
from typing import AsyncIterator, Dict, List, Optional, Any
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.llm.base import BaseLLMClient, ChatResponse, ToolCall

logger = structlog.get_logger(__name__)


class NVIDIAClient(BaseLLMClient):
    """Client for NVIDIA NIM API.
    
    Supports:
    - Chat completions with tool calling
    - Streaming responses
    - Nemotron models for reasoning
    - NeMo Retriever for embeddings
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0
    ):
        """Initialize NVIDIA client.
        
        Args:
            api_key: NVIDIA API key (defaults to settings)
            base_url: API base URL (defaults to settings)
            model: Default model to use (defaults to settings)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.nvidia_api_key
        self.base_url = (base_url or settings.nvidia_base_url).rstrip("/")
        self.model = model or settings.nvidia_model
        self.timeout = timeout
        
        if not self.api_key:
            logger.warning("NVIDIA API key not configured")
        
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers=self._get_headers()
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False
    ) -> ChatResponse:
        """Send chat completion request.
        
        Args:
            messages: List of message dicts with role and content
            tools: Optional list of tool definitions (OpenAI format)
            model: Model to use (defaults to instance model)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            stream: Whether to stream response
            
        Returns:
            ChatResponse with content and optional tool calls
        """
        url = f"{self.base_url}/chat/completions"
        model = model or self.model
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        logger.debug(
            "NVIDIA chat request",
            model=model,
            message_count=len(messages),
            has_tools=bool(tools)
        )
        
        try:
            if stream:
                return await self._stream_chat(url, payload)
            else:
                return await self._sync_chat(url, payload)
        except httpx.HTTPError as e:
            logger.error("NVIDIA API error", error=str(e))
            raise NVIDIAAPIError(f"NVIDIA API request failed: {e}") from e
    
    async def _sync_chat(self, url: str, payload: Dict) -> ChatResponse:
        """Non-streaming chat completion."""
        response = await self._client.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        choice = data["choices"][0]
        message = choice["message"]
        
        # Parse tool calls if present
        tool_calls = None
        if message.get("tool_calls"):
            tool_calls = [
                ToolCall(
                    id=tc["id"],
                    name=tc["function"]["name"],
                    arguments=json.loads(tc["function"]["arguments"])
                )
                for tc in message["tool_calls"]
            ]
        
        return ChatResponse(
            content=message.get("content", ""),
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason", "stop"),
            usage=data.get("usage")
        )
    
    async def _stream_chat(self, url: str, payload: Dict) -> ChatResponse:
        """Streaming chat completion - collects full response."""
        content_parts = []
        tool_calls_data = {}
        finish_reason = "stop"
        
        async with self._client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                
                data_str = line[6:]  # Remove "data: " prefix
                if data_str == "[DONE]":
                    break
                
                try:
                    data = json.loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    
                    # Collect content
                    if "content" in delta and delta["content"]:
                        content_parts.append(delta["content"])
                    
                    # Collect tool calls
                    if "tool_calls" in delta:
                        for tc in delta["tool_calls"]:
                            idx = tc["index"]
                            if idx not in tool_calls_data:
                                tool_calls_data[idx] = {
                                    "id": tc.get("id", ""),
                                    "name": tc.get("function", {}).get("name", ""),
                                    "arguments": ""
                                }
                            if tc.get("function", {}).get("arguments"):
                                tool_calls_data[idx]["arguments"] += tc["function"]["arguments"]
                    
                    finish_reason = data["choices"][0].get("finish_reason") or finish_reason
                    
                except json.JSONDecodeError:
                    continue
        
        # Build tool calls
        tool_calls = None
        if tool_calls_data:
            tool_calls = [
                ToolCall(
                    id=tc["id"],
                    name=tc["name"],
                    arguments=json.loads(tc["arguments"]) if tc["arguments"] else {}
                )
                for tc in tool_calls_data.values()
            ]
        
        return ChatResponse(
            content="".join(content_parts),
            tool_calls=tool_calls,
            finish_reason=finish_reason
        )
    
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream chat completion yielding chunks.
        
        Yields dicts with:
        - type: "content" | "tool_call" | "done"
        - data: chunk data
        """
        url = f"{self.base_url}/chat/completions"
        model = model or self.model
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        async with self._client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                
                data_str = line[6:]
                if data_str == "[DONE]":
                    yield {"type": "done", "data": {}}
                    break
                
                try:
                    data = json.loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    
                    if "content" in delta and delta["content"]:
                        yield {"type": "content", "data": {"delta": delta["content"]}}
                    
                    if "tool_calls" in delta:
                        yield {"type": "tool_call", "data": {"tool_calls": delta["tool_calls"]}}
                        
                except json.JSONDecodeError:
                    continue
    
    async def embed(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            model: Embedding model (defaults to NeMo Retriever)
            
        Returns:
            List of embedding vectors
        """
        url = f"{self.base_url}/embeddings"
        model = model or settings.nvidia_embedding_model
        
        payload = {
            "model": model,
            "input": texts,
            "input_type": "query"
        }
        
        response = await self._client.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        return [item["embedding"] for item in data["data"]]
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class NVIDIAAPIError(Exception):
    """NVIDIA API error."""
    pass
