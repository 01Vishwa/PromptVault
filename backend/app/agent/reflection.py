"""
Reflexion Module
================

Self-critique and improvement for agent responses.
Evaluates answers against quality criteria and regenerates if needed.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import structlog

from app.llm.client import get_llm_client
from app.llm.prompts import get_prompt

logger = structlog.get_logger(__name__)


class QualityCriterion(str, Enum):
    """Quality evaluation criteria."""
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    CITATIONS = "citations"
    CLARITY = "clarity"
    RELEVANCE = "relevance"


@dataclass
class CritiqueResult:
    """Result from critiquing a response."""
    overall_score: float  # 0-10
    scores: Dict[QualityCriterion, float]
    issues: List[str]
    suggestions: List[str]
    passed: bool  # meets threshold


@dataclass
class ReflexionResult:
    """Result from Reflexion process."""
    final_answer: str
    original_answer: str
    improved: bool
    critique: Optional[CritiqueResult]
    iterations: int


class ReflexionModule:
    """Reflexion module for self-critique and improvement.
    
    Implements the Reflexion pattern:
    1. Generate initial response
    2. Critique against quality criteria
    3. If below threshold, regenerate with feedback
    4. Repeat until passing or max iterations
    
    Quality Criteria:
    - Accuracy: Facts are correct and verifiable
    - Completeness: Addresses all aspects of query
    - Citations: Sources properly cited
    - Clarity: Clear and well-organized
    - Relevance: Stays on topic
    
    Example:
        reflexion = ReflexionModule()
        result = await reflexion.improve(
            query="What is quantum computing?",
            draft="Quantum computing uses qubits...",
            sources=[{"url": "...", "title": "..."}]
        )
        print(result.final_answer)
    """
    
    def __init__(self, threshold: float = 7.0, max_iterations: int = 2):
        """Initialize Reflexion module.
        
        Args:
            threshold: Minimum score to pass (0-10)
            max_iterations: Maximum improvement iterations
        """
        self.threshold = threshold
        self.max_iterations = max_iterations
        self.llm = get_llm_client()
        self.critic_prompt = get_prompt("reflexion_critic")
        self.improver_prompt = get_prompt("reflexion_improver")
    
    async def evaluate(
        self,
        query: str,
        response: str,
        sources: List[Dict] = None
    ) -> CritiqueResult:
        """Evaluate a response against quality criteria.
        
        Args:
            query: Original query
            response: Response to evaluate
            sources: Optional sources for citation checking
            
        Returns:
            CritiqueResult with scores and feedback
        """
        sources = sources or []
        
        # Build context for critic
        source_info = "\n".join([
            f"[{i+1}] {s.get('title', 'Untitled')} - {s.get('url', '')}"
            for i, s in enumerate(sources)
        ]) if sources else "No sources provided"
        
        messages = [
            {"role": "system", "content": self.critic_prompt},
            {"role": "user", "content": (
                f"Query: {query}\n\n"
                f"Response to evaluate:\n{response}\n\n"
                f"Available sources:\n{source_info}\n\n"
                "Evaluate this response against all quality criteria."
            )}
        ]
        
        try:
            llm_response = await self.llm.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=1000
            )
            
            return self._parse_critique(llm_response.content)
            
        except Exception as e:
            logger.error(f"Critique failed: {e}")
            # REL-001: Return failing critique on error instead of silently passing
            return CritiqueResult(
                overall_score=0.0,
                scores={c: 0.0 for c in QualityCriterion},
                issues=[f"Critique evaluation failed: {str(e)}"],
                suggestions=["Retry the evaluation or review manually"],
                passed=False
            )
    
    def _parse_critique(self, content: str) -> CritiqueResult:
        """Parse LLM critique response.
        
        Args:
            content: LLM response with critique
            
        Returns:
            CritiqueResult parsed from response
        """
        import re
        
        # Extract overall score
        overall_score = 7.0  # Default
        score_match = re.search(r'overall[:\s]*(\d+(?:\.\d+)?)', content.lower())
        if score_match:
            overall_score = float(score_match.group(1))
        
        # Extract individual scores
        scores = {}
        for criterion in QualityCriterion:
            pattern = rf'{criterion.value}[:\s]*(\d+(?:\.\d+)?)'
            match = re.search(pattern, content.lower())
            if match:
                scores[criterion] = float(match.group(1))
            else:
                scores[criterion] = overall_score
        
        # Extract issues
        issues = []
        issues_match = re.search(r'issues?[:\s]*\n(.*?)(?:\n\n|suggestions?|$)', content, re.IGNORECASE | re.DOTALL)
        if issues_match:
            issues = [
                line.strip().lstrip('- •')
                for line in issues_match.group(1).split('\n')
                if line.strip() and len(line.strip()) > 5
            ]
        
        # Extract suggestions
        suggestions = []
        sugg_match = re.search(r'suggestions?[:\s]*\n(.*?)(?:\n\n|$)', content, re.IGNORECASE | re.DOTALL)
        if sugg_match:
            suggestions = [
                line.strip().lstrip('- •')
                for line in sugg_match.group(1).split('\n')
                if line.strip() and len(line.strip()) > 5
            ]
        
        return CritiqueResult(
            overall_score=overall_score,
            scores=scores,
            issues=issues[:5],  # Limit to top 5
            suggestions=suggestions[:5],
            passed=overall_score >= self.threshold
        )
    
    async def improve(
        self,
        query: str,
        draft: str,
        sources: List[Dict] = None
    ) -> ReflexionResult:
        """Improve a response through self-critique.
        
        Args:
            query: Original query
            draft: Initial response to improve
            sources: Sources for citation checking
            
        Returns:
            ReflexionResult with final answer
        """
        sources = sources or []
        current_answer = draft
        final_critique = None
        
        logger.info("Starting Reflexion", query=query[:50])
        
        for iteration in range(self.max_iterations):
            # Evaluate current answer
            critique = await self.evaluate(query, current_answer, sources)
            final_critique = critique
            
            logger.debug(
                f"Reflexion iteration {iteration + 1}",
                score=critique.overall_score,
                passed=critique.passed
            )
            
            if critique.passed:
                return ReflexionResult(
                    final_answer=current_answer,
                    original_answer=draft,
                    improved=iteration > 0,
                    critique=critique,
                    iterations=iteration + 1
                )
            
            # Generate improved version
            current_answer = await self._regenerate(
                query=query,
                draft=current_answer,
                critique=critique,
                sources=sources
            )
        
        # Return best effort after max iterations
        return ReflexionResult(
            final_answer=current_answer,
            original_answer=draft,
            improved=True,
            critique=final_critique,
            iterations=self.max_iterations
        )
    
    async def _regenerate(
        self,
        query: str,
        draft: str,
        critique: CritiqueResult,
        sources: List[Dict]
    ) -> str:
        """Regenerate response with critique feedback.
        
        Args:
            query: Original query
            draft: Current response
            critique: Critique with issues to fix
            sources: Available sources
            
        Returns:
            Improved response
        """
        # Format feedback
        issues_text = "\n".join([f"- {issue}" for issue in critique.issues])
        suggestions_text = "\n".join([f"- {s}" for s in critique.suggestions])
        
        source_info = "\n".join([
            f"[{i+1}] {s.get('title', 'Untitled')} - {s.get('url', '')}"
            for i, s in enumerate(sources)
        ]) if sources else "No sources"
        
        messages = [
            {"role": "system", "content": self.improver_prompt},
            {"role": "user", "content": (
                f"Query: {query}\n\n"
                f"Current response:\n{draft}\n\n"
                f"Score: {critique.overall_score}/10\n\n"
                f"Issues to fix:\n{issues_text}\n\n"
                f"Suggestions:\n{suggestions_text}\n\n"
                f"Available sources:\n{source_info}\n\n"
                "Rewrite the response addressing all issues."
            )}
        ]
        
        response = await self.llm.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=2048
        )
        
        return response.content


# Singleton
_module: Optional[ReflexionModule] = None


def get_reflexion() -> ReflexionModule:
    """Get or create singleton Reflexion module."""
    global _module
    if _module is None:
        _module = ReflexionModule()
    return _module
