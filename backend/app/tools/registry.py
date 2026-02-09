"""
Tool Registry
=============

Central registry for discovering and managing tools.
Provides tool lookup, schema export, and parallel execution.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass
import structlog

from app.tools.base import BaseTool, ToolResult

logger = structlog.get_logger(__name__)


@dataclass
class ToolExecution:
    """Result of a tool execution request."""
    tool_name: str
    result: ToolResult
    duration_ms: float


class ToolRegistry:
    """Central registry for all available tools.
    
    Features:
    - Tool registration and discovery
    - OpenAI schema export
    - Parallel tool execution
    - Execution timeout handling
    
    Usage:
        registry = ToolRegistry()
        registry.register(WebSearchTool())
        registry.register(CalculatorTool())
        
        # Get schemas for LLM
        tools = registry.get_openai_tools()
        
        # Execute a tool
        result = await registry.execute("web_search", query="AI news")
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._tools: Dict[str, BaseTool] = {}
        logger.info("Tool registry initialized")
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool in the registry.
        
        Args:
            tool: Tool instance to register
            
        Raises:
            ValueError: If tool with same name already registered
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        
        self._tools[tool.name] = tool
        logger.info(f"Tool registered: {tool.name}")
    
    def register_class(self, tool_class: Type[BaseTool]) -> None:
        """Register a tool class (instantiates automatically).
        
        Args:
            tool_class: Tool class to instantiate and register
        """
        tool = tool_class()
        self.register(tool)
    
    def unregister(self, name: str) -> bool:
        """Remove a tool from the registry.
        
        Args:
            name: Tool name to remove
            
        Returns:
            True if removed, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Tool unregistered: {name}")
            return True
        return False
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """Get list of all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Get all tools in OpenAI function calling format.
        
        Returns:
            List of tool schemas for LLM
        """
        return [tool.to_openai_schema() for tool in self._tools.values()]
    
    def get_tool_descriptions(self) -> str:
        """Get human-readable tool descriptions.
        
        Returns:
            Formatted string of tool descriptions
        """
        lines = ["Available tools:"]
        for name, tool in self._tools.items():
            lines.append(f"- {name}: {tool.description}")
        return "\n".join(lines)
    
    async def execute(
        self,
        name: str,
        timeout: float = 30.0,
        **kwargs
    ) -> ToolResult:
        """Execute a tool by name.
        
        Args:
            name: Tool name
            timeout: Execution timeout in seconds
            **kwargs: Tool arguments
            
        Returns:
            ToolResult from execution
        """
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool not found: {name}"
            )
        
        try:
            result = await asyncio.wait_for(
                tool.safe_execute(**kwargs),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Tool {name} timed out after {timeout}s")
            return ToolResult(
                success=False,
                error=f"Tool execution timed out after {timeout} seconds"
            )
    
    async def execute_parallel(
        self,
        calls: List[Dict[str, Any]],
        timeout: float = 30.0
    ) -> List[ToolExecution]:
        """Execute multiple tools in parallel.
        
        Args:
            calls: List of dicts with 'name' and 'args' keys
            timeout: Timeout per tool execution
            
        Returns:
            List of ToolExecution results
        """
        async def execute_one(call: Dict) -> ToolExecution:
            name = call.get("name", "")
            args = call.get("args", {})
            
            start = time.perf_counter()
            result = await self.execute(name, timeout=timeout, **args)
            duration = (time.perf_counter() - start) * 1000
            
            return ToolExecution(
                tool_name=name,
                result=result,
                duration_ms=duration
            )
        
        logger.info(f"Executing {len(calls)} tools in parallel")
        
        tasks = [execute_one(call) for call in calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        executions = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                executions.append(ToolExecution(
                    tool_name=calls[i].get("name", "unknown"),
                    result=ToolResult(success=False, error=str(result)),
                    duration_ms=0
                ))
            else:
                executions.append(result)
        
        return executions
    
    def __len__(self) -> int:
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        return name in self._tools


# =============================================================================
# Singleton Registry
# =============================================================================

_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get or create the global tool registry.
    
    Returns:
        ToolRegistry singleton instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _register_default_tools(_registry)
    return _registry


def _register_default_tools(registry: ToolRegistry) -> None:
    """Register all default tools.
    
    Args:
        registry: Registry to populate
    """
    # Import here to avoid circular imports
    from app.tools.web_search import WebSearchTool
    from app.tools.web_scraper import WebScraperTool
    from app.tools.calculator import CalculatorTool
    
    registry.register(WebSearchTool())
    registry.register(WebScraperTool())
    registry.register(CalculatorTool())
    
    logger.info(f"Registered {len(registry)} default tools")
