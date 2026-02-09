"""
Tree Search Agent
=================

.. deprecated::
    This module is deprecated and will be removed in a future version.
    Use the multi-agent workflow (app.agent.multi_agent.workflow) instead
    for complex analysis queries. The multi-agent system provides better
    orchestration, parallel execution, and quality assurance.

Explores multiple solution approaches for complex queries.
Generates distinct strategies, evaluates them, and synthesizes the best.
"""

import warnings
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import asyncio
import re
import structlog

from app.llm.client import get_llm_client
from app.llm.prompts import get_prompt
from app.agent.react import ReACTAgent

logger = structlog.get_logger(__name__)

# Deprecation warning
warnings.warn(
    "TreeSearchAgent is deprecated. Use multi-agent workflow instead.",
    DeprecationWarning,
    stacklevel=2
)

# PERF-003: Pre-compiled regex patterns
_APPROACH_PATTERN = re.compile(r'APPROACH\s*\d+[:\s]*', re.IGNORECASE)
_SCORE_PATTERN = re.compile(r'(\d+(?:\.\d+)?)')


@dataclass
class Approach:
    """A potential solution approach."""
    id: str
    description: str
    strategy: str
    key_questions: List[str] = field(default_factory=list)


@dataclass
class PathResult:
    """Result from exploring an approach."""
    approach: Approach
    answer: str
    sources: List[Dict]
    score: float
    reasoning: str


@dataclass
class TreeSearchResult:
    """Result from Tree Search agent."""
    final_answer: str
    best_approach: Approach
    all_paths: List[PathResult]
    sources: List[Dict]
    success: bool


class TreeSearchAgent:
    """Tree Search agent for complex analysis queries.
    
    For open-ended or complex questions, generates multiple
    distinct approaches, explores each, then synthesizes
    the best results.
    
    Process:
    1. GENERATE: Create K distinct approaches
    2. EXPLORE: Execute each approach (can use ReACT)
    3. EVALUATE: Score each path's results
    4. SYNTHESIZE: Combine best insights
    
    Example:
        agent = TreeSearchAgent(branching_factor=3)
        result = await agent.run("What's the future of AI regulation?")
        # Explores regulatory, technical, and economic perspectives
    """
    
    def __init__(
        self,
        branching_factor: int = 3,
        max_depth: int = 1
    ):
        """Initialize Tree Search agent.
        
        Args:
            branching_factor: Number of approaches to generate (K)
            max_depth: Depth of search (1 = single level)
        """
        self.k = branching_factor
        self.max_depth = max_depth
        self.llm = get_llm_client()
        self.system_prompt = get_prompt("tree_search")
        self.react_agent = ReACTAgent(max_iterations=3)
    
    async def run(self, query: str) -> TreeSearchResult:
        """Execute Tree Search for a query.
        
        Args:
            query: Complex query to analyze
            
        Returns:
            TreeSearchResult with best answer and all paths
        """
        logger.info("Starting Tree Search", query=query[:100], k=self.k)
        
        try:
            # Step 1: Generate approaches
            approaches = await self._generate_approaches(query)
            logger.info(f"Generated {len(approaches)} approaches")
            
            # Step 2: Explore each approach in parallel
            paths = await self._explore_all(query, approaches)
            
            # Step 3: Find best path
            best_path = max(paths, key=lambda p: p.score)
            
            # Step 4: Synthesize final answer
            final_answer = await self._synthesize(query, paths, best_path)
            
            # Collect all sources
            all_sources = []
            for path in paths:
                all_sources.extend(path.sources)
            
            # Deduplicate sources by URL
            seen_urls = set()
            unique_sources = []
            for source in all_sources:
                url = source.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_sources.append(source)
            
            return TreeSearchResult(
                final_answer=final_answer,
                best_approach=best_path.approach,
                all_paths=paths,
                sources=unique_sources,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Tree Search error: {e}")
            return TreeSearchResult(
                final_answer="Unable to complete analysis.",
                best_approach=Approach(id="error", description="Error", strategy=""),
                all_paths=[],
                sources=[],
                success=False
            )
    
    async def _generate_approaches(self, query: str) -> List[Approach]:
        """Generate K distinct approaches to the query.
        
        Args:
            query: User's question
            
        Returns:
            List of Approach objects
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": (
                f"Generate {self.k} distinct approaches to answer this query:\n\n"
                f"{query}\n\n"
                "For each approach, provide:\n"
                "1. A unique perspective or angle\n"
                "2. The research strategy\n"
                "3. Key questions to answer\n\n"
                "Format each approach as:\n"
                "APPROACH 1: [Title]\n"
                "Strategy: [How to approach]\n"
                "Questions: [What to research]\n"
            )}
        ]
        
        response = await self.llm.chat(
            messages=messages,
            temperature=0.8,  # Higher temp for diversity
            max_tokens=1500
        )
        
        return self._parse_approaches(response.content)
    
    def _parse_approaches(self, content: str) -> List[Approach]:
        """Parse LLM response into Approach objects.
        
        Args:
            content: LLM response with approaches
            
        Returns:
            List of Approach objects
        """
        approaches = []
        
        # Split by APPROACH pattern
        sections = _APPROACH_PATTERN.split(content)
        
        for i, section in enumerate(sections[1:], 1):  # Skip empty first split
            if not section.strip():
                continue
            
            lines = section.strip().split('\n')
            title = lines[0].strip() if lines else f"Approach {i}"
            
            # Extract strategy
            strategy = ""
            strategy_match = re.search(r'Strategy[:\s]*(.*?)(?:Questions|$)', section, re.IGNORECASE | re.DOTALL)
            if strategy_match:
                strategy = strategy_match.group(1).strip()
            
            # Extract questions
            questions = []
            questions_match = re.search(r'Questions[:\s]*(.*?)(?:APPROACH|$)', section, re.IGNORECASE | re.DOTALL)
            if questions_match:
                q_text = questions_match.group(1)
                questions = [
                    q.strip().lstrip('- •0123456789.)') 
                    for q in q_text.split('\n') 
                    if q.strip() and len(q.strip()) > 5
                ][:3]  # Max 3 questions
            
            approaches.append(Approach(
                id=f"approach_{i}",
                description=title,
                strategy=strategy or title,
                key_questions=questions
            ))
        
        # Ensure we have at least one approach
        if not approaches:
            approaches.append(Approach(
                id="approach_1",
                description="General research",
                strategy="Search for relevant information and synthesize",
                key_questions=["What are the key facts?"]
            ))
        
        return approaches[:self.k]  # Limit to K approaches
    
    async def _explore_all(
        self,
        query: str,
        approaches: List[Approach]
    ) -> List[PathResult]:
        """Explore all approaches in parallel.
        
        Args:
            query: Original query
            approaches: Approaches to explore
            
        Returns:
            List of PathResult for each approach
        """
        async def explore_one(approach: Approach) -> PathResult:
            logger.debug(f"Exploring: {approach.description}")
            
            # Build focused query for this approach
            focused_query = (
                f"{query}\n\n"
                f"Approach: {approach.description}\n"
                f"Strategy: {approach.strategy}\n"
                f"Focus on: {', '.join(approach.key_questions)}"
            )
            
            # Use ReACT to explore this path
            result = await self.react_agent.run(focused_query)
            
            # Score this path
            score = await self._score_path(query, approach, result.answer)
            
            return PathResult(
                approach=approach,
                answer=result.answer,
                sources=result.sources,
                score=score,
                reasoning=f"Explored via {len(result.steps)} steps"
            )
        
        # Execute in parallel
        results = await asyncio.gather(
            *[explore_one(approach) for approach in approaches],
            return_exceptions=True
        )
        
        # Handle exceptions
        paths = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                paths.append(PathResult(
                    approach=approaches[i],
                    answer=f"Exploration failed: {result}",
                    sources=[],
                    score=0.0,
                    reasoning="Error during exploration"
                ))
            else:
                paths.append(result)
        
        return paths
    
    async def _score_path(
        self,
        query: str,
        approach: Approach,
        answer: str
    ) -> float:
        """Score a path's results.
        
        Args:
            query: Original query
            approach: The approach used
            answer: The generated answer
            
        Returns:
            Score from 0-10
        """
        messages = [
            {"role": "system", "content": (
                "You are an evaluator scoring answer quality. "
                "Rate from 0-10 based on relevance, completeness, "
                "accuracy, and usefulness. Return ONLY a number."
            )},
            {"role": "user", "content": (
                f"Query: {query}\n\n"
                f"Approach: {approach.description}\n\n"
                f"Answer:\n{answer[:1000]}\n\n"
                "Score (0-10):"
            )}
        ]
        
        try:
            response = await self.llm.chat(
                messages=messages,
                temperature=0.1,
                max_tokens=10
            )
            
            # Extract number from response
            match = _SCORE_PATTERN.search(response.content)
            if match:
                return min(10.0, float(match.group(1)))
            return 5.0
            
        except Exception:
            return 5.0  # Default score on error
    
    async def _synthesize(
        self,
        query: str,
        paths: List[PathResult],
        best_path: PathResult
    ) -> str:
        """Synthesize final answer from all paths.
        
        Args:
            query: Original query
            paths: All explored paths
            best_path: Highest scoring path
            
        Returns:
            Synthesized final answer
        """
        # Build context from all paths
        paths_context = []
        for path in sorted(paths, key=lambda p: p.score, reverse=True):
            paths_context.append(
                f"### {path.approach.description} (Score: {path.score:.1f})\n"
                f"{path.answer[:800]}"
            )
        
        messages = [
            {"role": "system", "content": (
                "You are an expert synthesizer. Combine insights from "
                "multiple research approaches into a comprehensive answer. "
                "Prioritize the highest-scoring approaches but include "
                "unique insights from others. Use citations [1], [2] etc."
            )},
            {"role": "user", "content": (
                f"Query: {query}\n\n"
                f"Research from {len(paths)} approaches:\n\n"
                f"{chr(10).join(paths_context)}\n\n"
                "Synthesize the best comprehensive answer."
            )}
        ]
        
        response = await self.llm.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=2048
        )
        
        return response.content


# Singleton
_agent: Optional[TreeSearchAgent] = None


def get_tree_search_agent() -> TreeSearchAgent:
    """Get or create singleton Tree Search agent."""
    global _agent
    if _agent is None:
        _agent = TreeSearchAgent()
    return _agent
