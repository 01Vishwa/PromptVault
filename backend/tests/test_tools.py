"""
Tool System Tests
=================

Tests for the tool system (base, registry, individual tools).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestBaseTool:
    """Test BaseTool class."""
    
    def test_tool_requires_name(self):
        """Test that tool requires a name."""
        from app.tools.base import BaseTool, ToolResult
        
        class NoNameTool(BaseTool):
            name = ""
            description = "Has description"
            
            async def execute(self, **kwargs):
                return ToolResult(success=True)
        
        with pytest.raises(ValueError, match="must have a name"):
            NoNameTool()
    
    def test_tool_requires_description(self):
        """Test that tool requires a description."""
        from app.tools.base import BaseTool, ToolResult
        
        class NoDescTool(BaseTool):
            name = "test"
            description = ""
            
            async def execute(self, **kwargs):
                return ToolResult(success=True)
        
        with pytest.raises(ValueError, match="must have a description"):
            NoDescTool()
    
    def test_openai_schema_format(self):
        """Test OpenAI schema generation."""
        from app.tools.base import BaseTool, ToolResult
        
        class TestTool(BaseTool):
            name = "test_tool"
            description = "A test tool"
            parameters = {
                "type": "object",
                "properties": {
                    "input": {"type": "string"}
                }
            }
            
            async def execute(self, **kwargs):
                return ToolResult(success=True)
        
        tool = TestTool()
        schema = tool.to_openai_schema()
        
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "test_tool"
        assert schema["function"]["description"] == "A test tool"


class TestToolRegistry:
    """Test ToolRegistry class."""
    
    def test_register_tool(self):
        """Test tool registration."""
        from app.tools.registry import ToolRegistry
        from app.tools.base import BaseTool, ToolResult
        
        class MockTool(BaseTool):
            name = "mock_tool"
            description = "A mock tool"
            
            async def execute(self, **kwargs):
                return ToolResult(success=True)
        
        registry = ToolRegistry()
        registry.register(MockTool())
        
        assert "mock_tool" in registry
        assert len(registry) == 1
    
    def test_duplicate_registration_raises(self):
        """Test that duplicate registration raises error."""
        from app.tools.registry import ToolRegistry
        from app.tools.base import BaseTool, ToolResult
        
        class MockTool(BaseTool):
            name = "mock_tool"
            description = "A mock tool"
            
            async def execute(self, **kwargs):
                return ToolResult(success=True)
        
        registry = ToolRegistry()
        registry.register(MockTool())
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register(MockTool())
    
    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        """Test executing unknown tool returns error."""
        from app.tools.registry import ToolRegistry
        
        registry = ToolRegistry()
        result = await registry.execute("unknown_tool")
        
        assert result.success is False
        assert "not found" in result.error


class TestCalculatorTool:
    """Test CalculatorTool (SEC-005 validation)."""
    
    @pytest.mark.asyncio
    async def test_basic_calculation(self):
        """Test basic math operations."""
        from app.tools.calculator import CalculatorTool
        
        tool = CalculatorTool()
        result = await tool.execute(expression="2 + 2")
        
        assert result.success is True
        assert "4" in str(result.data)
    
    @pytest.mark.asyncio
    async def test_safe_eval_prevents_builtins(self):
        """SEC-005: Test that unsafe expressions are blocked."""
        from app.tools.calculator import CalculatorTool
        
        tool = CalculatorTool()
        
        # These should fail or return safely
        result = await tool.execute(expression="__import__('os')")
        assert result.success is False
