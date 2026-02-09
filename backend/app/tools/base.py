"""
Base Tool
=========

Abstract base class for all tools in Axiom AI.
Defines the interface for tool definition, validation, and execution.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class ToolStatus(str, Enum):
    """Tool execution status."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class ToolResult:
    """Result from tool execution.
    
    Attributes:
        success: Whether the tool executed successfully
        data: The result data (varies by tool)
        error: Error message if failed
        sources: List of source citations (for search tools)
        metadata: Additional metadata about execution
    """
    success: bool
    data: Any = None
    error: Optional[str] = None
    sources: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_observation(self) -> str:
        """Convert result to observation string for agent.
        
        Returns:
            String representation suitable for agent context
        """
        if not self.success:
            return f"Error: {self.error}"
        
        if isinstance(self.data, str):
            return self.data
        
        if isinstance(self.data, list):
            return "\n".join(str(item) for item in self.data)
        
        return str(self.data)


class BaseTool(ABC):
    """Abstract base class for all tools.
    
    Subclasses must implement:
    - name: Tool identifier
    - description: What the tool does
    - parameters: OpenAI-format parameter schema
    - execute(): Async execution logic
    
    Example:
        class MyTool(BaseTool):
            name = "my_tool"
            description = "Does something useful"
            parameters = {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Input value"}
                },
                "required": ["input"]
            }
            
            async def execute(self, input: str) -> ToolResult:
                result = do_something(input)
                return ToolResult(success=True, data=result)
    """
    
    # Override in subclasses
    name: str = ""
    description: str = ""
    parameters: Optional[Dict[str, Any]] = None
    
    def __init__(self):
        """Initialize the tool."""
        if self.parameters is None:
            self.parameters = {}
        if not self.name:
            raise ValueError("Tool must have a name")
        if not self.description:
            raise ValueError("Tool must have a description")
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert tool to OpenAI function calling format.
        
        Returns:
            Dict in OpenAI tool format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    def validate_args(self, **kwargs) -> bool:
        """Validate arguments against parameter schema.
        
        Args:
            **kwargs: Arguments to validate
            
        Returns:
            True if valid, raises ValueError if not
        """
        required = self.parameters.get("required", [])
        properties = self.parameters.get("properties", {})
        
        # Check required parameters
        for param in required:
            if param not in kwargs:
                raise ValueError(f"Missing required parameter: {param}")
        
        # Check parameter types (basic validation)
        for key, value in kwargs.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type == "string" and not isinstance(value, str):
                    raise ValueError(f"Parameter {key} must be a string")
                if expected_type == "integer" and not isinstance(value, int):
                    raise ValueError(f"Parameter {key} must be an integer")
                if expected_type == "number" and not isinstance(value, (int, float)):
                    raise ValueError(f"Parameter {key} must be a number")
                if expected_type == "boolean" and not isinstance(value, bool):
                    raise ValueError(f"Parameter {key} must be a boolean")
                if expected_type == "array" and not isinstance(value, list):
                    raise ValueError(f"Parameter {key} must be an array")
        
        return True
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given arguments.
        
        Args:
            **kwargs: Tool-specific arguments
            
        Returns:
            ToolResult with execution outcome
        """
        pass
    
    async def safe_execute(self, **kwargs) -> ToolResult:
        """Execute with error handling and logging.
        
        Args:
            **kwargs: Tool-specific arguments
            
        Returns:
            ToolResult with execution outcome
        """
        logger.info(f"Executing tool: {self.name}", args=kwargs)
        
        try:
            # Validate arguments
            self.validate_args(**kwargs)
            
            # Execute
            result = await self.execute(**kwargs)
            
            logger.info(
                f"Tool {self.name} completed",
                success=result.success,
                has_sources=len(result.sources) > 0
            )
            
            return result
            
        except ValueError as e:
            logger.warning(f"Tool {self.name} validation error", error=str(e))
            return ToolResult(
                success=False,
                error=f"Validation error: {e}"
            )
        except Exception as e:
            logger.error(f"Tool {self.name} execution error", error=str(e))
            return ToolResult(
                success=False,
                error=f"Execution error: {e}"
            )
    
    def __repr__(self) -> str:
        return f"<Tool: {self.name}>"
