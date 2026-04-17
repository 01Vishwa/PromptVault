from langchain_core.tools import BaseTool, tool

@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        return str(eval(expression, {"__builtins__": None}, {}))
    except Exception as e:
        return f"Error: {e}"

@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    return f"Weather in {location} is sunny, 72F."

@tool
def search_web(query: str) -> str:
    """Search the web for a query."""
    return f"Search results for: {query}. Here is a summary of relevant information."

@tool
def write_file(content: str, filepath: str) -> str:
    """Write content to a file."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        return f"Error: {e}"

TOOL_REGISTRY = {
    "calculator": calculator,
    "get_weather": get_weather,
    "search_web": search_web,
    "write_file": write_file
}

if __name__ == "__main__":
    print(calculator.invoke("8 * 7"))
