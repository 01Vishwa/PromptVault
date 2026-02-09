"""
ReWOO Agent
===========

Reasoning WithOut Observation - plans all steps upfront before execution.
Reduces latency by enabling parallel tool execution.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
import asyncio
import re
import structlog

from app.llm.client import get_llm_client
from app.llm.prompts import get_prompt
from app.tools.registry import get_registry, ToolRegistry

logger = structlog.get_logger(__name__)


@dataclass
class PlanStep:
    """A single step in the execution plan."""
    step_id: str
    tool: str
    args: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    result: Optional[str] = None
    completed: bool = False


@dataclass
class ReWOOResult:
    """Result from ReWOO agent execution."""
    answer: str
    plan: List[PlanStep]
    sources: List[Dict]
    success: bool
    error: Optional[str] = None


class ReWOOAgent:
    """ReWOO (Reasoning WithOut Observation) Agent.
    
    Unlike ReACT which interleaves reasoning and acting,
    ReWOO plans all steps upfront then executes them.
    
    Advantages:
    - Parallel execution of independent steps
    - Reduced LLM calls
    - Lower latency for multi-step queries
    
    Process:
    1. PLAN: Generate complete execution plan
    2. EXECUTE: Run steps (parallel when possible)
    3. SYNTHESIZE: Combine results into answer
    
    Example:
        agent = ReWOOAgent()
        result = await agent.run("Compare NVIDIA and AMD 2024 performance")
        # Steps for NVIDIA and AMD searches run in parallel
    """
    
    def __init__(self, tool_registry: ToolRegistry = None):
        """Initialize ReWOO agent.
        
        Args:
            tool_registry: Tool registry to use (defaults to global)
        """
        self.llm = get_llm_client()
        self.tools = tool_registry or get_registry()
        self.planner_prompt = get_prompt("rewoo")
    
    async def run(self, query: str) -> ReWOOResult:
        """Execute ReWOO for a query.
        
        Args:
            query: User's question
            
        Returns:
            ReWOOResult with answer and execution details
        """
        logger.info("Starting ReWOO", query=query[:100])
        
        try:
            # Step 1: Generate plan
            plan = await self._generate_plan(query)
            
            if not plan:
                return ReWOOResult(
                    answer="Unable to generate execution plan.",
                    plan=[],
                    sources=[],
                    success=False,
                    error="Planning failed"
                )
            
            logger.info(f"Generated plan with {len(plan)} steps")
            
            # Step 2: Execute plan
            all_sources = await self._execute_plan(plan)
            
            # Step 3: Synthesize answer
            answer = await self._synthesize(query, plan)
            
            return ReWOOResult(
                answer=answer,
                plan=plan,
                sources=all_sources,
                success=True
            )
            
        except Exception as e:
            logger.error(f"ReWOO error: {e}")
            return ReWOOResult(
                answer="",
                plan=[],
                sources=[],
                success=False,
                error=str(e)
            )
    
    async def _generate_plan(self, query: str) -> List[PlanStep]:
        """Generate execution plan from query.
        
        Args:
            query: User's question
            
        Returns:
            List of plan steps
        """
        # Get available tools description
        tool_desc = self.tools.get_tool_descriptions()
        
        messages = [
            {"role": "system", "content": self.planner_prompt},
            {"role": "user", "content": f"{tool_desc}\n\nQuery: {query}"}
        ]
        
        response = await self.llm.chat(
            messages=messages,
            temperature=0.3,  # Low temp for structured output
            max_tokens=2000
        )
        
        return self._parse_plan(response.content)
    
    def _parse_plan(self, content: str) -> List[PlanStep]:
        """Parse LLM plan output into structured steps.
        
        Expected format:
        #1: web_search(query="NVIDIA 2024") -> nvidia_results
        #2: web_search(query="AMD 2024") -> amd_results
        #3: synthesize(nvidia_results, amd_results) -> final
        
        Args:
            content: LLM response with plan
            
        Returns:
            List of PlanStep objects
        """
        steps = []
        
        # Pattern: #N: tool_name(args) [depends: #X, #Y]
        pattern = r'#(\d+):\s*(\w+)\((.*?)\)(?:\s*->\s*(\w+))?(?:\s*\[depends:\s*(.*?)\])?'
        
        for match in re.finditer(pattern, content, re.IGNORECASE):
            step_num = match.group(1)
            tool_name = match.group(2)
            args_str = match.group(3)
            output_var = match.group(4)
            deps_str = match.group(5)
            
            # Parse arguments
            args = self._parse_args(args_str)
            
            # Parse dependencies
            deps = []
            if deps_str:
                deps = [f"#{d.strip()}" for d in deps_str.replace('#', '').split(',')]
            
            steps.append(PlanStep(
                step_id=f"#{step_num}",
                tool=tool_name,
                args=args,
                depends_on=deps
            ))
        
        # If no structured plan found, create a simple one
        if not steps:
            steps.append(PlanStep(
                step_id="#1",
                tool="web_search",
                args={"query": content[:200]},
                depends_on=[]
            ))
        
        return steps
    
    def _parse_args(self, args_str: str) -> Dict[str, Any]:
        """Parse tool arguments from string.
        
        Args:
            args_str: Arguments like 'query="test", num=5'
            
        Returns:
            Dict of parsed arguments
        """
        args = {}
        
        # Pattern for key="value" or key=value
        pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\' ([^\']*)\'|(\S+))'
        
        for match in re.finditer(pattern, args_str):
            key = match.group(1)
            # Get whichever group matched
            value = match.group(2) or match.group(3) or match.group(4)
            
            # Try to convert to appropriate type
            if value.isdigit():
                value = int(value)
            elif value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            
            args[key] = value
        
        return args
    
    async def _execute_plan(self, plan: List[PlanStep]) -> List[Dict]:
        """Execute plan steps, parallelizing where possible.
        
        Args:
            plan: List of plan steps
            
        Returns:
            List of all sources collected
        """
        all_sources = []
        completed: Set[str] = set()
        max_iterations = len(plan) * 2  # Safety limit to prevent infinite loops
        iteration = 0
        
        while len(completed) < len(plan) and iteration < max_iterations:
            iteration += 1
            
            # Find steps ready to execute (deps satisfied)
            ready = [
                step for step in plan
                if step.step_id not in completed
                and all(dep in completed for dep in step.depends_on)
            ]
            
            if not ready:
                # REL-003: Detect cycle and break with error logging
                remaining = [s.step_id for s in plan if s.step_id not in completed]
                logger.error(
                    "Cycle detected in plan execution",
                    remaining=remaining,
                    completed=list(completed)
                )
                break
            
            # Execute ready steps in parallel
            logger.debug(f"Executing {len(ready)} steps in parallel")
            
            async def execute_step(step: PlanStep):
                if step.tool not in self.tools:
                    step.result = f"Tool not found: {step.tool}"
                    return []
                
                # Replace variable references in args
                resolved_args = self._resolve_args(step.args, plan)
                
                result = await self.tools.execute(step.tool, **resolved_args)
                step.result = result.to_observation()
                step.completed = True
                
                return result.sources
            
            results = await asyncio.gather(
                *[execute_step(step) for step in ready],
                return_exceptions=True
            )
            
            for step, result in zip(ready, results):
                completed.add(step.step_id)
                if isinstance(result, list):
                    all_sources.extend(result)
        
        return all_sources
    
    def _resolve_args(self, args: Dict, plan: List[PlanStep]) -> Dict:
        """Resolve variable references in arguments.
        
        Args:
            args: Arguments potentially containing variable refs
            plan: Full plan for variable lookup
            
        Returns:
            Args with variables resolved to values
        """
        resolved = {}
        
        for key, value in args.items():
            if isinstance(value, str) and value.startswith('#'):
                # Find the referenced step
                ref_id = value.split('_')[0]  # e.g., "#1_results" -> "#1"
                for step in plan:
                    if step.step_id == ref_id and step.result:
                        resolved[key] = step.result
                        break
                else:
                    resolved[key] = value  # Keep original if not found
            else:
                resolved[key] = value
        
        return resolved
    
    async def _synthesize(self, query: str, plan: List[PlanStep]) -> str:
        """Synthesize final answer from plan results.
        
        Args:
            query: Original query
            plan: Executed plan with results
            
        Returns:
            Synthesized answer
        """
        # Build context from results
        context_parts = []
        for step in plan:
            if step.result:
                context_parts.append(f"[{step.step_id}] {step.tool}: {step.result[:500]}")
        
        context = "\n\n".join(context_parts)
        
        messages = [
            {"role": "system", "content": (
                "You are an expert at synthesizing information into clear, "
                "well-cited answers. Use the research results to answer "
                "the user's query. Include citations using [#N] format."
            )},
            {"role": "user", "content": (
                f"Query: {query}\n\n"
                f"Research Results:\n{context}\n\n"
                "Provide a comprehensive answer with citations."
            )}
        ]
        
        response = await self.llm.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=2048
        )
        
        return response.content


# Singleton
_agent: Optional[ReWOOAgent] = None


def get_rewoo_agent() -> ReWOOAgent:
    """Get or create singleton ReWOO agent."""
    global _agent
    if _agent is None:
        _agent = ReWOOAgent()
    return _agent
