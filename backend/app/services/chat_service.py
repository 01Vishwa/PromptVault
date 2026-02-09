"""
Chat Service
=============

Business logic for chat operations.
Handles query processing, agent coordination, and response formatting.
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from urllib.parse import urlparse
import structlog

from app.agent.router import get_router, QueryType, RouterResult
from app.agent.react import get_react_agent, ReACTResult, ReACTAgent
from app.agent.rewoo import get_rewoo_agent
from app.agent.reflection import get_reflexion
from app.agent.multi_agent.workflow import run_research_pipeline
from app.llm.client import get_llm_client
from app.models.request import SearchDepth

logger = structlog.get_logger(__name__)


@dataclass
class ProcessedResponse:
    """Processed chat response."""
    answer: str
    sources: List[Dict]
    thinking_steps: List[str]
    tool_calls: List[str]
    query_type: QueryType
    provider: str
    duration_ms: int


class ChatService:
    """Service for processing chat queries.
    
    Coordinates between:
    - Query Router (classification)
    - Agents (ReACT, ReWOO, Tree Search)
    - Reflexion (quality improvement)
    
    Example:
        service = ChatService()
        result = await service.process(
            query="Compare Tesla vs Rivian",
            search_depth=SearchDepth.DEEP,
            enable_reflection=True
        )
    """
    
    def __init__(self):
        """Initialize chat service."""
        self.router = get_router()
        self.llm = get_llm_client()
    
    async def process(
        self,
        query: str,
        search_depth: SearchDepth = SearchDepth.NORMAL,
        enable_reflection: bool = True,
        max_sources: int = 5
    ) -> ProcessedResponse:
        """Process a chat query end-to-end.
        
        Args:
            query: User's question
            search_depth: How deep to search
            enable_reflection: Whether to apply Reflexion
            max_sources: Maximum sources to return
            
        Returns:
            ProcessedResponse with answer and metadata
        """
        start_time = time.perf_counter()
        
        logger.info("Processing query", query=query[:100], depth=search_depth.value)
        
        # Classify query
        classification = await self.router.classify(query)
        
        # Route to appropriate handler
        if classification.query_type == QueryType.SIMPLE:
            result = await self._handle_simple(query)
        elif classification.query_type == QueryType.SEARCH:
            result = await self._handle_search(query)
        elif classification.query_type == QueryType.RESEARCH:
            result = await self._handle_research(query, search_depth)
        else:  # ANALYSIS
            result = await self._handle_analysis(query)
        
        # Apply Reflexion if enabled
        if enable_reflection and result["answer"]:
            reflexion = get_reflexion()
            improved = await reflexion.improve(
                query=query,
                draft=result["answer"],
                sources=result["sources"]
            )
            result["answer"] = improved.final_answer
            if improved.improved:
                logger.info("Response improved by Reflexion")
        
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Format citations
        formatted_sources = self._format_sources(
            result["sources"],
            max_sources
        )
        
        return ProcessedResponse(
            answer=result["answer"],
            sources=formatted_sources,
            thinking_steps=result.get("thinking_steps", []),
            tool_calls=result.get("tool_calls", []),
            query_type=classification.query_type,
            provider=result.get("provider", "unknown"),
            duration_ms=duration_ms
        )
    
    async def _handle_simple(self, query: str) -> Dict[str, Any]:
        """Handle simple query with direct LLM."""
        response = await self.llm.chat(
            messages=[
                {"role": "system", "content": (
                    "You are a helpful assistant. Provide clear, accurate answers. "
                    "If you're not certain about something, say so."
                )},
                {"role": "user", "content": query}
            ],
            temperature=0.7,
            max_tokens=1024
        )
        
        return {
            "answer": response.content,
            "sources": [],
            "thinking_steps": [],
            "tool_calls": [],
            "provider": self.llm.last_provider.value if self.llm.last_provider else "llm"
        }
    
    async def _handle_search(self, query: str) -> Dict[str, Any]:
        """Handle search query with limited ReACT."""
        agent = ReACTAgent(max_iterations=2)
        result = await agent.run(query)
        
        return self._format_react_result(result)
    
    async def _handle_research(
        self,
        query: str,
        depth: SearchDepth
    ) -> Dict[str, Any]:
        """Handle research query with full agent."""
        if depth == SearchDepth.QUICK:
            agent = get_react_agent()
            result = await agent.run(query)
            return self._format_react_result(result)
        else:
            # Use ReWOO for parallel execution
            agent = get_rewoo_agent()
            result = await agent.run(query)
            
            return {
                "answer": result.answer,
                "sources": result.sources,
                "thinking_steps": [f"Step: {s.tool}({list(s.args.keys())})" for s in result.plan],
                "tool_calls": [s.tool for s in result.plan],
                "provider": "rewoo"
            }
    
    async def _handle_analysis(self, query: str) -> Dict[str, Any]:
        """Handle analysis query with Multi-Agent Workflow.
        
        ARCH-001: Aligned with chat.py to use multi-agent instead of TreeSearch.
        """
        result = await run_research_pipeline(query)
        
        # Extract thinking steps from messages
        thinking_steps = []
        for msg in result.messages:
            if msg.metadata.get("action"):
                thinking_steps.append(f"{msg.sender.value}: {msg.metadata.get('action')}")
        
        return {
            "answer": result.final_answer or result.draft_answer or "Unable to generate response",
            "sources": result.sources,
            "thinking_steps": thinking_steps if thinking_steps else [
                f"Orchestrated {len(result.subtasks)} research tasks",
                f"Collected {len(result.sources)} sources",
                f"Completed in {result.iteration} iteration(s)"
            ],
            "tool_calls": [f"subtask: {t.description[:50]}" for t in result.subtasks],
            "provider": "multi_agent"
        }
    
    def _format_react_result(self, result: ReACTResult) -> Dict[str, Any]:
        """Format ReACT result to standard format."""
        return {
            "answer": result.answer,
            "sources": result.sources,
            "thinking_steps": [
                s.content for s in result.steps 
                if s.step_type.value == "thought"
            ],
            "tool_calls": [
                s.tool_name for s in result.steps 
                if s.tool_name
            ],
            "provider": "react"
        }
    
    def _format_sources(
        self,
        sources: List[Dict],
        max_sources: int
    ) -> List[Dict]:
        """Format and deduplicate sources."""
        seen_urls = set()
        unique = []
        
        for source in sources:
            url = source.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append({
                    "id": len(unique) + 1,
                    "title": source.get("title", "Untitled"),
                    "url": url,
                    "snippet": source.get("snippet", "")[:300],
                    "domain": source.get("domain", self._extract_domain(url))
                })
            
            if len(unique) >= max_sources:
                break
        
        return unique
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc.replace("www.", "")
        except Exception:
            return ""


# Singleton
_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Get or create singleton chat service."""
    global _service
    if _service is None:
        _service = ChatService()
    return _service
