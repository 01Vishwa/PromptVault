"""
Query Router
============

Classifies incoming queries and routes them to the appropriate agent.
Uses LLM to understand query complexity and intent.
"""

from typing import Dict, Any, Optional, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass
import re
import structlog

from app.llm.client import get_llm_client, ChatResponse
from app.llm.prompts import get_prompt

logger = structlog.get_logger(__name__)

# PERF-003: Pre-compiled regex patterns
_CONFIDENCE_PATTERN = re.compile(r'confidence[:\s]*(\d+(?:\.\d+)?)', re.IGNORECASE)


class QueryType(str, Enum):
    """Query classification types."""
    SIMPLE = "SIMPLE"       # Direct answer, no search needed
    SEARCH = "SEARCH"       # Single search, quick answer
    RESEARCH = "RESEARCH"   # Multi-step research, ReACT pattern
    ANALYSIS = "ANALYSIS"   # Complex analysis, Tree Search


@dataclass
class RouterResult:
    """Result from query routing."""
    query_type: QueryType
    confidence: float
    reasoning: str
    suggested_approach: str


class QueryRouter:
    """Routes queries to appropriate agents based on complexity.
    
    Classification:
    - SIMPLE: Factual questions answerable without web search
    - SEARCH: Questions requiring a single web search
    - RESEARCH: Multi-step questions requiring multiple searches
    - ANALYSIS: Complex questions requiring multiple approaches
    
    Example:
        router = QueryRouter()
        result = await router.classify("What is 2+2?")
        # result.query_type == QueryType.SIMPLE
        
        result = await router.classify("Compare Tesla vs Rivian sales 2024")
        # result.query_type == QueryType.RESEARCH
    """
    
    def __init__(self):
        """Initialize the query router."""
        self.llm = get_llm_client()
        self.system_prompt = get_prompt("router")
    
    async def classify(self, query: str) -> RouterResult:
        """Classify a query into a type.
        
        Args:
            query: User's question
            
        Returns:
            RouterResult with type and reasoning
        """
        logger.info("Classifying query", query=query[:100])
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Classify this query:\n\n{query}"}
        ]
        
        try:
            response = await self.llm.chat(
                messages=messages,
                temperature=0.1,  # Low temp for consistent classification
                max_tokens=500
            )
            
            result = self._parse_classification(response.content)
            
            logger.info(
                "Query classified",
                query_type=result.query_type.value,
                confidence=result.confidence
            )
            
            return result
            
        except Exception as e:
            logger.error("Classification failed", error=str(e))
            # Default to RESEARCH on failure (safe fallback)
            return RouterResult(
                query_type=QueryType.RESEARCH,
                confidence=0.5,
                reasoning="Classification failed, defaulting to research",
                suggested_approach="Use ReACT agent with web search"
            )
    
    def _parse_classification(self, content: str) -> RouterResult:
        """Parse LLM classification response.
        
        Args:
            content: LLM response content
            
        Returns:
            RouterResult parsed from response
        """
        content_upper = content.upper()
        
        # Detect query type from response
        if "SIMPLE" in content_upper:
            query_type = QueryType.SIMPLE
        elif "ANALYSIS" in content_upper:
            query_type = QueryType.ANALYSIS
        elif "RESEARCH" in content_upper:
            query_type = QueryType.RESEARCH
        elif "SEARCH" in content_upper:
            query_type = QueryType.SEARCH
        else:
            # Default based on content heuristics
            query_type = QueryType.RESEARCH
        
        # Extract confidence if present
        confidence = 0.8  # Default confidence
        if "confidence" in content.lower():
            match = _CONFIDENCE_PATTERN.search(content)
            if match:
                confidence = min(1.0, float(match.group(1)) / 100)
        
        return RouterResult(
            query_type=query_type,
            confidence=confidence,
            reasoning=content[:200],
            suggested_approach=self._get_approach(query_type)
        )
    
    def _get_approach(self, query_type: QueryType) -> str:
        """Get suggested approach for query type."""
        approaches = {
            QueryType.SIMPLE: "Direct LLM response without tools",
            QueryType.SEARCH: "Single web search + synthesis",
            QueryType.RESEARCH: "ReACT agent with multiple tool calls",
            QueryType.ANALYSIS: "Multi-agent workflow with orchestrator, researchers, and critic"
        }
        return approaches.get(query_type, "ReACT agent")
    
    async def route_and_execute(
        self,
        query: str,
        handlers: Dict[QueryType, Callable[[str], Awaitable[str]]]
    ) -> str:
        """Classify query and execute appropriate handler.
        
        Args:
            query: User's question
            handlers: Dict mapping QueryType to async handler functions
            
        Returns:
            Response from the appropriate handler
        """
        result = await self.classify(query)
        
        if result.query_type in handlers:
            return await handlers[result.query_type](query)
        
        # Fallback to RESEARCH handler if available
        if QueryType.RESEARCH in handlers:
            return await handlers[QueryType.RESEARCH](query)
        
        raise ValueError(f"No handler for query type: {result.query_type}")


# Singleton instance
_router: Optional[QueryRouter] = None


def get_router() -> QueryRouter:
    """Get or create the singleton router."""
    global _router
    if _router is None:
        _router = QueryRouter()
    return _router
