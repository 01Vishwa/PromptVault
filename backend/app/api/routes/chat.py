"""
Chat Routes
===========

Main API endpoints for chat functionality.
Supports both synchronous and streaming responses.
"""

import uuid
import time
import json
from typing import AsyncIterator, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import structlog

from app.models.request import ChatRequest, SearchDepth
from app.models.response import (
    ChatStartResponse,
    ChatResponse,
    StreamEvent,
    StreamEventType,
    Citation,
    ErrorResponse
)
from app.agent.router import get_router, QueryType
from app.agent.react import get_react_agent, ReACTAgent
from app.agent.rewoo import get_rewoo_agent
from app.agent.reflection import get_reflexion
from app.agent.multi_agent.workflow import run_research_pipeline
from app.llm.client import get_llm_client

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


# =============================================================================
# Synchronous Chat Endpoint
# =============================================================================

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat query and return the complete response.
    
    This endpoint blocks until the full response is ready.
    For real-time updates, use the streaming endpoint.
    
    Args:
        request: Chat request with query and settings
        
    Returns:
        Complete chat response with answer and sources
    """
    start_time = time.perf_counter()
    
    logger.info("Chat request", query=request.query[:100])
    
    try:
        # Get query router
        query_router = get_router()
        
        # Classify query
        classification = await query_router.classify(request.query)
        logger.info(f"Query classified as {classification.query_type.value}")
        
        # Route to appropriate agent
        if classification.query_type == QueryType.SIMPLE:
            # Direct LLM response
            result = await _handle_simple(request.query)
        elif classification.query_type == QueryType.SEARCH:
            # Quick search with ReACT (limited iterations)
            result = await _handle_search(request.query)
        elif classification.query_type == QueryType.RESEARCH:
            # Full ReACT or ReWOO based on depth
            result = await _handle_research(request.query, request.settings.search_depth)
        else:  # ANALYSIS
            # Tree Search for complex queries
            result = await _handle_analysis(request.query)
        
        # Apply Reflexion if enabled
        if request.settings.enable_reflection and result["answer"]:
            reflexion = get_reflexion()
            improved = await reflexion.improve(
                query=request.query,
                draft=result["answer"],
                sources=result["sources"]
            )
            result["answer"] = improved.final_answer
        
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        
        return ChatResponse(
            query=request.query,
            answer=result["answer"],
            sources=[
                Citation(
                    id=i + 1,
                    title=s.get("title", ""),
                    url=s.get("url", ""),
                    snippet=s.get("snippet", ""),
                    domain=s.get("domain", "")
                )
                for i, s in enumerate(result["sources"][:request.settings.max_sources])
            ],
            thinking_steps=result.get("thinking_steps", []),
            tool_calls=result.get("tool_calls", []),
            duration_ms=duration_ms,
            provider=result.get("provider", "unknown")
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_simple(query: str) -> dict:
    """Handle simple query with direct LLM response."""
    llm = get_llm_client()
    
    response = await llm.chat(
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Provide a clear, concise answer."},
            {"role": "user", "content": query}
        ],
        temperature=0.7,
        max_tokens=1024
    )
    
    return {
        "answer": response.content,
        "sources": [],
        "provider": llm.last_provider.value if llm.last_provider else "unknown"
    }


async def _handle_search(query: str) -> dict:
    """Handle search query with limited ReACT."""
    # PERF-001: Use singleton agent for search (limited iterations)
    agent = get_react_agent()
    # Create a new agent only when we need different max_iterations
    if agent.max_iterations != 2:
        agent = ReACTAgent(max_iterations=2)
    result = await agent.run(query)
    
    return {
        "answer": result.answer,
        "sources": result.sources,
        "thinking_steps": [s.content for s in result.steps if s.step_type.value == "thought"],
        "tool_calls": [s.tool_name for s in result.steps if s.tool_name],
        "provider": "react"
    }


async def _handle_research(query: str, depth: SearchDepth) -> dict:
    """Handle research query with full agent."""
    if depth == SearchDepth.QUICK:
        agent = get_react_agent()
    else:
        # Use ReWOO for deeper research (parallel execution)
        agent = get_rewoo_agent()
    
    result = await agent.run(query)
    
    if hasattr(result, 'steps'):
        # ReACT result
        return {
            "answer": result.answer,
            "sources": result.sources,
            "thinking_steps": [s.content for s in result.steps if s.step_type.value == "thought"],
            "tool_calls": [s.tool_name for s in result.steps if s.tool_name],
            "provider": "react"
        }
    else:
        # ReWOO result
        return {
            "answer": result.answer,
            "sources": result.sources,
            "thinking_steps": [f"Plan step: {s.tool}" for s in result.plan],
            "tool_calls": [s.tool for s in result.plan],
            "provider": "rewoo"
        }


async def _handle_analysis(query: str) -> dict:
    """Handle analysis query with Multi-Agent Workflow.
    
    Uses the orchestrator-researcher-synthesizer-critic pipeline
    for complex queries requiring deep research and quality checks.
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


# =============================================================================
# Streaming Chat Endpoint
# =============================================================================

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat response in real-time using Server-Sent Events.
    
    Events are sent as JSON with type and data fields:
    - thinking: Agent reasoning step
    - action: Tool being called
    - observation: Tool result
    - content: Answer content chunk
    - sources: Source citations
    - done: Completion with metadata
    
    Args:
        request: Chat request with query and settings
        
    Returns:
        SSE stream of events
    """
    logger.info("Stream request", query=request.query[:100])
    
    async def event_generator() -> AsyncIterator[dict]:
        start_time = time.perf_counter()
        
        try:
            # Initial event
            yield {
                "event": "start",
                "data": json.dumps({
                    "type": "start",
                    "data": {"query": request.query}
                })
            }
            
            # Classify query
            query_router = get_router()
            classification = await query_router.classify(request.query)
            
            yield {
                "event": "classification",
                "data": json.dumps({
                    "type": "classification",
                    "data": {
                        "query_type": classification.query_type.value,
                        "reasoning": classification.reasoning[:200]
                    }
                })
            }
            
            # Stream based on query type
            # ARCH-003: All query types now get appropriate handling
            all_sources = []
            final_answer = ""
            
            if classification.query_type == QueryType.SIMPLE:
                # Stream direct LLM response
                llm = get_llm_client()
                
                async for chunk in llm.stream_chat(
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": request.query}
                    ]
                ):
                    if chunk["type"] == "content":
                        final_answer += chunk["data"]["delta"]
                        yield {
                            "event": "content",
                            "data": json.dumps({
                                "type": "content",
                                "data": {"delta": chunk["data"]["delta"]}
                            })
                        }
            else:
                # Stream ReACT agent
                agent = get_react_agent()
                
                async for event in agent.stream(request.query):
                    event_type = event["type"]
                    event_data = event["data"]
                    
                    if event_type == "thought":
                        yield {
                            "event": "thinking",
                            "data": json.dumps({
                                "type": "thinking",
                                "data": {"thought": event_data["content"]}
                            })
                        }
                    
                    elif event_type == "action":
                        yield {
                            "event": "action",
                            "data": json.dumps({
                                "type": "tool_call",
                                "data": {
                                    "tool": event_data["tool"],
                                    "args": event_data["args"]
                                }
                            })
                        }
                    
                    elif event_type == "observation":
                        if event_data.get("sources"):
                            all_sources.extend(event_data["sources"])
                        
                        yield {
                            "event": "observation",
                            "data": json.dumps({
                                "type": "tool_result",
                                "data": {
                                    "success": event_data.get("success", True),
                                    "content": event_data["content"][:500]
                                }
                            })
                        }
                    
                    elif event_type == "answer":
                        final_answer = event_data["content"]
                        all_sources = event_data.get("sources", all_sources)
                        
                        # Stream answer in chunks for smooth display
                        chunks = _chunk_text(final_answer, 50)
                        for chunk in chunks:
                            yield {
                                "event": "content",
                                "data": json.dumps({
                                    "type": "content",
                                    "data": {"delta": chunk}
                                })
                            }
            
            # Send sources
            if all_sources:
                yield {
                    "event": "sources",
                    "data": json.dumps({
                        "type": "sources",
                        "data": {
                            "sources": [
                                {
                                    "id": i + 1,
                                    "title": s.get("title", ""),
                                    "url": s.get("url", ""),
                                    "snippet": s.get("snippet", "")[:200]
                                }
                                for i, s in enumerate(all_sources[:request.settings.max_sources])
                            ]
                        }
                    })
                }
            
            # Done event
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            
            yield {
                "event": "done",
                "data": json.dumps({
                    "type": "done",
                    "data": {
                        "duration_ms": duration_ms,
                        "sources_count": len(all_sources)
                    }
                })
            }
            
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "type": "error",
                    "data": {"error": str(e)}
                })
            }
    
    return EventSourceResponse(event_generator())


def _chunk_text(text: str, chunk_size: int) -> list:
    """Split text into chunks for streaming."""
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


# =============================================================================
# Citation Management
# =============================================================================

@router.get("/sources/{source_id}")
async def get_source_details(source_id: int):
    """Get detailed information about a source citation.
    
    Note: This endpoint is planned for future implementation.
    Sources are currently returned inline with responses.
    
    Args:
        source_id: The citation ID from the response
        
    Returns:
        Placeholder response indicating feature is planned
        
    Raises:
        HTTPException: 501 Not Implemented
    """
    raise HTTPException(
        status_code=501,
        detail={
            "message": "Source lookup not yet implemented",
            "source_id": source_id,
            "workaround": "Sources are returned inline with chat responses"
        }
    )
