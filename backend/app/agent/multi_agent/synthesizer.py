"""
Synthesizer Agent
=================

Composes research findings into coherent, well-cited responses.

The Synthesizer:
1. Receives research results from Researcher(s)
2. Organizes information logically
3. Writes a cohesive answer with inline citations
4. Formats sources for the final response
"""

import json
from typing import List, Dict
import structlog

from app.llm.client import get_llm_client
from app.agent.multi_agent.state import AgentState, AgentRole

logger = structlog.get_logger(__name__)


SYNTHESIS_PROMPT = """You are a synthesis specialist. Your job is to combine research findings into a clear, well-organized response.

Guidelines:
1. **Lead with the answer** — Start with the most important conclusion
2. **Use inline citations** — Reference sources as [1], [2], etc.
3. **Be comprehensive** — Cover all key aspects from the research
4. **Stay factual** — Only include information from the provided research
5. **Use structure** — Headers and bullets for complex topics

Format your response with:
- A clear answer to the original question
- Supporting details with citations
- A "Sources" section at the end listing all references

Example citation format:
"According to recent data, NVIDIA leads in AI chip revenue [1], while AMD has gained market share [2]."
"""


class SynthesizerAgent:
    """Synthesizer agent for composing final responses.
    
    Takes accumulated research results and combines them into
    a coherent, well-cited answer.
    
    Example:
        synthesizer = SynthesizerAgent()
        state = await synthesizer.synthesize(state)
        # state.draft_answer now contains the composed response
    """
    
    def __init__(self):
        """Initialize synthesizer."""
        self.llm = get_llm_client()
        
    async def synthesize(self, state: AgentState) -> AgentState:
        """Synthesize research results into a draft answer.
        
        Combines all research findings into a coherent response
        with proper citations.
        
        Args:
            state: State with research results
            
        Returns:
            State with draft_answer populated
        """
        if not state.research_results:
            logger.warning("No research results to synthesize")
            state.draft_answer = "I couldn't find relevant information to answer this question."
            return state
        
        logger.info(
            "Synthesizer starting",
            result_count=len(state.research_results),
            source_count=len(state.sources)
        )
        
        # Build context from research
        context = self._build_context(state)
        
        # Build source reference
        sources_ref = self._build_source_reference(state.sources)
        
        try:
            response = await self.llm.chat(
                messages=[
                    {"role": "system", "content": SYNTHESIS_PROMPT},
                    {"role": "user", "content": f"""Original Question: {state.query}

Research Findings:
{context}

Available Sources (use [1], [2], etc. to cite):
{sources_ref}

Now synthesize these findings into a comprehensive answer with citations."""}
                ],
                temperature=0.5,
                max_tokens=2048
            )
            
            state.draft_answer = response.content
            
            # Log synthesis
            state.add_message(
                sender=AgentRole.SYNTHESIZER,
                receiver=AgentRole.CRITIC,
                content=json.dumps({
                    "action": "synthesis_complete",
                    "answer_length": len(state.draft_answer)
                })
            )
            
            logger.info(
                "Synthesis complete",
                answer_length=len(state.draft_answer)
            )
            
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            # Create basic synthesis from research
            state.draft_answer = self._fallback_synthesis(state)
            
        return state
    
    def _build_context(self, state: AgentState) -> str:
        """Build context string from research results."""
        parts = []
        for i, result in enumerate(state.research_results, 1):
            task_id = result.get("task_id", f"research_{i}")
            answer = result.get("answer", "")
            parts.append(f"### Finding {i} ({task_id})\n{answer}\n")
        return "\n".join(parts)
    
    def _build_source_reference(self, sources: List[Dict]) -> str:
        """Build numbered source reference list."""
        lines = []
        for i, source in enumerate(sources[:10], 1):
            title = source.get("title", "Unknown")
            url = source.get("url", "")
            lines.append(f"[{i}] {title} - {url}")
        return "\n".join(lines)
    
    def _fallback_synthesis(self, state: AgentState) -> str:
        """Create basic synthesis when LLM fails."""
        parts = [f"Based on research about: {state.query}\n"]
        
        for i, result in enumerate(state.research_results, 1):
            answer = result.get("answer", "")[:500]
            parts.append(f"\n**Finding {i}:**\n{answer}")
        
        if state.sources:
            parts.append("\n\n**Sources:**")
            for i, source in enumerate(state.sources[:5], 1):
                parts.append(f"[{i}] {source.get('title', 'Source')} - {source.get('url', '')}")
        
        return "\n".join(parts)


# Factory function
_synthesizer: SynthesizerAgent = None


def get_synthesizer() -> SynthesizerAgent:
    """Get or create the synthesizer agent instance."""
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = SynthesizerAgent()
    return _synthesizer
