"""
Critic Agent
============

Quality assurance agent for fact-checking and improvement.

The Critic:
1. Evaluates draft answers for accuracy and quality
2. Checks that claims are supported by sources
3. Identifies issues and suggests improvements
4. Decides whether to APPROVE or request REVISION
"""

import json
from typing import Dict, Any
import structlog

from app.llm.client import get_llm_client
from app.agent.multi_agent.state import AgentState, AgentRole

logger = structlog.get_logger(__name__)


CRITIQUE_PROMPT = """You are a quality assurance critic. Evaluate the draft answer for accuracy and quality.

## Evaluation Criteria

1. **Accuracy** (0-10): Are claims factually correct and supported by sources?
2. **Completeness** (0-10): Does it fully answer the question?
3. **Citations** (0-10): Are sources properly cited with [1], [2] format?
4. **Clarity** (0-10): Is it well-organized and easy to read?

## Your Response

Respond with a JSON object:
```json
{
    "scores": {
        "accuracy": 8,
        "completeness": 7,
        "citations": 9,
        "clarity": 8
    },
    "overall_score": 8.0,
    "verdict": "APPROVE" or "REVISE",
    "issues": [
        "Issue 1 description",
        "Issue 2 description"
    ],
    "suggestions": [
        "Improvement suggestion 1",
        "Improvement suggestion 2"
    ]
}
```

## Guidelines
- **APPROVE** if overall_score >= 7.0 and no critical issues
- **REVISE** if hallucinations detected or major gaps exist
- Be specific about issues and actionable in suggestions
"""


class CriticAgent:
    """Critic agent for quality assurance.
    
    Evaluates synthesized answers and decides whether they
    are ready for the user or need revision.
    
    Example:
        critic = CriticAgent()
        state = await critic.critique(state)
        next_node = critic.should_revise(state)  # "finalize" or "research"
    """
    
    def __init__(self, threshold: float = 7.0):
        """Initialize critic.
        
        Args:
            threshold: Minimum score to approve (0-10)
        """
        self.llm = get_llm_client()
        self.threshold = threshold
        
    async def critique(self, state: AgentState) -> AgentState:
        """Evaluate the draft answer.
        
        Analyzes the current draft for quality issues and
        populates the critique field.
        
        Args:
            state: State with draft_answer
            
        Returns:
            State with critique populated
        """
        if not state.draft_answer:
            logger.warning("No draft answer to critique")
            state.critique = {
                "verdict": "REVISE",
                "issues": ["No draft answer available"],
                "overall_score": 0
            }
            return state
        
        logger.info("Critic evaluating draft")
        
        # Build source summary for verification
        sources_summary = self._summarize_sources(state.sources)
        
        try:
            response = await self.llm.chat(
                messages=[
                    {"role": "system", "content": CRITIQUE_PROMPT},
                    {"role": "user", "content": f"""Original Question: {state.query}

Draft Answer:
{state.draft_answer}

Available Sources for Verification:
{sources_summary}

Please evaluate this draft answer."""}
                ],
                temperature=0.3,
                max_tokens=1024
            )
            
            # Parse critique
            state.critique = self._parse_critique(response.content)
            
            # Increment iteration for revision tracking
            state.iteration += 1
            
            # Log critique
            state.add_message(
                sender=AgentRole.CRITIC,
                receiver=AgentRole.ORCHESTRATOR,
                content=json.dumps({
                    "action": "critique_complete",
                    "verdict": state.critique.get("verdict"),
                    "score": state.critique.get("overall_score"),
                    "iteration": state.iteration
                })
            )
            
            logger.info(
                "Critique complete",
                verdict=state.critique.get("verdict"),
                score=state.critique.get("overall_score")
            )
            
        except Exception as e:
            logger.error(f"Critique failed: {e}")
            # REL-002: Return REVISE on error instead of silently approving
            state.critique = {
                "verdict": "REVISE",
                "issues": [f"Critique evaluation failed: {str(e)}"],
                "suggestions": ["Manual review required due to evaluation error"],
                "overall_score": 0.0,
                "error": str(e)
            }
            
        return state
    
    def should_revise(self, state: AgentState) -> str:
        """Determine next node based on critique.
        
        This is the router function for conditional edges.
        
        Args:
            state: State with critique
            
        Returns:
            "finalize" if approved, "research" if needs revision
        """
        if not state.critique:
            return "finalize"
        
        verdict = state.critique.get("verdict", "APPROVE").upper()
        
        # Check iteration limit
        if not state.should_continue():
            logger.warning("Max iterations reached, forcing finalize")
            return "finalize"
        
        if verdict == "APPROVE":
            return "finalize"
        else:
            logger.info("Critic requested revision", iteration=state.iteration)
            return "research"
    
    def _parse_critique(self, content: str) -> Dict[str, Any]:
        """Parse LLM critique response."""
        try:
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
            
        except json.JSONDecodeError:
            logger.warning("Failed to parse critique as JSON")
            
            # Extract verdict from text
            verdict = "APPROVE" if "approve" in content.lower() else "REVISE"
            
            return {
                "verdict": verdict,
                "issues": [],
                "suggestions": [],
                "overall_score": self.threshold if verdict == "APPROVE" else 5.0,
                "raw_response": content[:500]
            }
    
    def _summarize_sources(self, sources: list) -> str:
        """Create source summary for verification."""
        lines = []
        for i, source in enumerate(sources[:10], 1):
            title = source.get("title", "Unknown")
            snippet = source.get("snippet", "")[:200]
            lines.append(f"[{i}] {title}\n    {snippet}")
        return "\n".join(lines)


# Factory function
_critic: CriticAgent = None


def get_critic() -> CriticAgent:
    """Get or create the critic agent instance."""
    global _critic
    if _critic is None:
        _critic = CriticAgent()
    return _critic
