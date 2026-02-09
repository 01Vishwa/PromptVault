"""
Calculator Tool
===============

Safe mathematical expression evaluator.
Supports basic arithmetic, common functions, and unit conversions.
"""

import math
import operator
import ast
from typing import Any, Dict, Optional, Union
import structlog

from app.tools.base import BaseTool, ToolResult

logger = structlog.get_logger(__name__)


class CalculatorTool(BaseTool):
    """Safe calculator for mathematical expressions.
    
    Uses AST parsing to safely evaluate expressions without
    the security risks of eval().
    
    Supported operations:
    - Basic arithmetic: +, -, *, /, **, //, %
    - Comparison: <, >, <=, >=, ==, !=
    - Functions: sqrt, sin, cos, tan, log, log10, exp, abs, round, floor, ceil
    - Constants: pi, e
    
    Examples:
    - "2 + 2" → 4
    - "sqrt(16) + 10" → 14.0
    - "sin(pi/2)" → 1.0
    - "100 * 1.08 ** 5" → 146.93... (compound interest)
    """
    
    name = "calculator"
    description = (
        "Evaluate mathematical expressions safely. "
        "Supports basic arithmetic (+, -, *, /, **), "
        "functions (sqrt, sin, cos, log, etc.), "
        "and constants (pi, e). "
        "Use this for any calculations or unit conversions."
    )
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16)', 'sin(pi/2)')"
            }
        },
        "required": ["expression"]
    }
    
    # Allowed operators
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    
    # Comparison operators
    COMPARISONS = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
    }
    
    # Allowed functions
    FUNCTIONS = {
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "sinh": math.sinh,
        "cosh": math.cosh,
        "tanh": math.tanh,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "exp": math.exp,
        "abs": abs,
        "round": round,
        "floor": math.floor,
        "ceil": math.ceil,
        "pow": pow,
        "min": min,
        "max": max,
        "sum": sum,
    }
    
    # Allowed constants
    CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
        "tau": math.tau,
        "inf": math.inf,
    }
    
    def __init__(self):
        """Initialize calculator tool."""
        super().__init__()
    
    async def execute(
        self,
        expression: str,
        **kwargs
    ) -> ToolResult:
        """Evaluate mathematical expression.
        
        Args:
            expression: Math expression string
            
        Returns:
            ToolResult with calculation result
        """
        expression = expression.strip()
        
        if not expression:
            return ToolResult(
                success=False,
                error="Empty expression"
            )
        
        logger.info(f"Calculating: {expression}")
        
        try:
            result = self._safe_eval(expression)
            
            # Format result
            if isinstance(result, float):
                # Round to reasonable precision
                if result == int(result):
                    result = int(result)
                else:
                    result = round(result, 10)
            
            observation = f"{expression} = {result}"
            
            return ToolResult(
                success=True,
                data=observation,
                metadata={
                    "expression": expression,
                    "result": result,
                    "type": type(result).__name__
                }
            )
            
        except ZeroDivisionError:
            return ToolResult(
                success=False,
                error="Division by zero"
            )
        except ValueError as e:
            return ToolResult(
                success=False,
                error=f"Math error: {e}"
            )
        except Exception as e:
            logger.warning(f"Calculator error: {e}")
            return ToolResult(
                success=False,
                error=f"Invalid expression: {e}"
            )
    
    def _safe_eval(self, expression: str) -> Union[int, float, bool]:
        """Safely evaluate expression using AST.
        
        Args:
            expression: Math expression
            
        Returns:
            Evaluated result
            
        Raises:
            ValueError: For invalid expressions
        """
        try:
            tree = ast.parse(expression, mode='eval')
        except SyntaxError as e:
            raise ValueError(f"Syntax error: {e}")
        
        return self._eval_node(tree.body)
    
    def _eval_node(self, node: ast.AST) -> Union[int, float, bool]:
        """Recursively evaluate AST node.
        
        Args:
            node: AST node
            
        Returns:
            Evaluated value
        """
        # Numbers
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant: {node.value}")
        
        # Names (constants)
        if isinstance(node, ast.Name):
            name = node.id.lower()
            if name in self.CONSTANTS:
                return self.CONSTANTS[name]
            raise ValueError(f"Unknown variable: {node.id}")
        
        # Unary operators (-, +)
        if isinstance(node, ast.UnaryOp):
            op = type(node.op)
            if op in self.OPERATORS:
                operand = self._eval_node(node.operand)
                return self.OPERATORS[op](operand)
            raise ValueError(f"Unsupported unary operator: {op}")
        
        # Binary operators (+, -, *, /, etc.)
        if isinstance(node, ast.BinOp):
            op = type(node.op)
            if op in self.OPERATORS:
                left = self._eval_node(node.left)
                right = self._eval_node(node.right)
                return self.OPERATORS[op](left, right)
            raise ValueError(f"Unsupported operator: {op}")
        
        # Comparisons
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                op_type = type(op)
                if op_type not in self.COMPARISONS:
                    raise ValueError(f"Unsupported comparison: {op_type}")
                right = self._eval_node(comparator)
                if not self.COMPARISONS[op_type](left, right):
                    return False
                left = right
            return True
        
        # Function calls
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Complex function calls not supported")
            
            func_name = node.func.id.lower()
            if func_name not in self.FUNCTIONS:
                raise ValueError(f"Unknown function: {func_name}")
            
            args = [self._eval_node(arg) for arg in node.args]
            return self.FUNCTIONS[func_name](*args)
        
        # Tuples/Lists (for functions like min, max)
        if isinstance(node, (ast.Tuple, ast.List)):
            return [self._eval_node(elt) for elt in node.elts]
        
        raise ValueError(f"Unsupported expression type: {type(node).__name__}")
