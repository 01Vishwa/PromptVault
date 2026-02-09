"""
Web Search Tool
===============

Tavily API integration for web search.
Optimized for LLM-friendly search results with source citations.
"""

from typing import Any, Dict, List, Optional
import httpx
import structlog

from app.config import settings
from app.tools.base import BaseTool, ToolResult

logger = structlog.get_logger(__name__)


class WebSearchTool(BaseTool):
    """Web search tool using Tavily API.
    
    Tavily is specifically designed for AI/LLM use cases,
    providing clean, relevant search results.
    
    Features:
    - Real-time web search
    - Source citation extraction
    - Relevance scoring
    - Domain filtering
    """
    
    name = "web_search"
    description = (
        "Search the web for current information on any topic. "
        "Returns relevant search results with titles, snippets, and URLs. "
        "Use this to find recent news, facts, data, or any information not in your training data."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query. Be specific and include relevant keywords."
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (1-10)",
                "default": 5
            },
            "search_depth": {
                "type": "string",
                "enum": ["basic", "advanced"],
                "description": "Search depth - 'advanced' for more thorough results",
                "default": "basic"
            },
            "include_domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of domains to include (e.g., ['reuters.com', 'bbc.com'])"
            },
            "exclude_domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of domains to exclude"
            }
        },
        "required": ["query"]
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize web search tool.
        
        Args:
            api_key: Tavily API key (defaults to settings)
        """
        super().__init__()
        self.api_key = api_key or settings.tavily_api_key
        self.base_url = "https://api.tavily.com"
        
        if not self.api_key:
            logger.warning("Tavily API key not configured")
    
    async def execute(
        self,
        query: str,
        num_results: int = 5,
        search_depth: str = "basic",
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        **kwargs
    ) -> ToolResult:
        """Execute web search.
        
        Args:
            query: Search query
            num_results: Number of results (1-10)
            search_depth: "basic" or "advanced"
            include_domains: Domains to include
            exclude_domains: Domains to exclude
            
        Returns:
            ToolResult with search results and sources
        """
        if not self.api_key:
            return ToolResult(
                success=False,
                error="Tavily API key not configured"
            )
        
        # Clamp num_results
        num_results = max(1, min(10, num_results))
        
        # Build request payload
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": num_results,
            "include_answer": True,
            "include_raw_content": False
        }
        
        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains
        
        logger.info(f"Searching: {query}", num_results=num_results)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
            
            # Parse results
            results = data.get("results", [])
            answer = data.get("answer", "")
            
            # Format sources
            sources = []
            formatted_results = []
            
            for i, result in enumerate(results, 1):
                source = {
                    "id": i,
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("content", "")[:500],
                    "domain": self._extract_domain(result.get("url", "")),
                    "score": result.get("score", 0)
                }
                sources.append(source)
                
                # Format for observation
                formatted_results.append(
                    f"[{i}] {source['title']}\n"
                    f"    URL: {source['url']}\n"
                    f"    {source['snippet'][:200]}..."
                )
            
            # Build observation text
            observation = f"Found {len(results)} results for: {query}\n\n"
            if answer:
                observation += f"Summary: {answer}\n\n"
            observation += "\n\n".join(formatted_results)
            
            return ToolResult(
                success=True,
                data=observation,
                sources=sources,
                metadata={
                    "query": query,
                    "result_count": len(results),
                    "has_answer": bool(answer)
                }
            )
            
        except httpx.HTTPError as e:
            logger.error(f"Tavily API error: {e}")
            return ToolResult(
                success=False,
                error=f"Search failed: {e}"
            )
        except Exception as e:
            logger.error(f"Search error: {e}")
            return ToolResult(
                success=False,
                error=f"Search error: {e}"
            )
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace("www.", "")
        except Exception:
            return ""
