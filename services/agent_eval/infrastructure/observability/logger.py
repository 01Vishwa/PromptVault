import json
from pathlib import Path
from datetime import datetime

class StructuredLogger:
    """JSONL logger — one entry per agent event. Thread-safe append."""
    def __init__(self, run_id: str, output_dir: Path = Path("results")):
        self.run_id = run_id
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / f"run_{run_id}.jsonl"
        self.start_time = datetime.utcnow()

    def emit(self, event_type: str, level: str = "INFO", **payload) -> None:
        from .tracer import OTelTracer
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "run_id": self.run_id,
            "span_id": OTelTracer.current_span_id(),
            "trace_id": OTelTracer.current_trace_id(),
            "event_type": event_type,
            "level": level,
            "payload": payload
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def close(self) -> None:
        elapsed_ms = int((datetime.utcnow() - self.start_time).total_seconds() * 1000)
        self.emit("SESSION_END", elapsed_ms=elapsed_ms)

    def llm_start(self, model: str, prompt_preview: str) -> None:
        self.emit("LLM_START", model=model, prompt_preview=prompt_preview)

    def llm_end(self, tokens_total: int, tokens_prompt: int, tokens_completion: int, response_preview: str) -> None:
        self.emit("LLM_END", tokens_total=tokens_total, tokens_prompt=tokens_prompt, 
                  tokens_completion=tokens_completion, response_preview=response_preview)

    def tool_start(self, tool_name: str, tool_input: str) -> None:
        self.emit("TOOL_START", tool_name=tool_name, tool_input=tool_input)

    def tool_end(self, tool_name: str, output_preview: str, output_length: int) -> None:
        self.emit("TOOL_END", tool_name=tool_name, output_preview=output_preview, output_length=output_length)

    def agent_action(self, tool: str, tool_input: str, thought: str) -> None:
        self.emit("AGENT_ACTION", tool=tool, tool_input=tool_input, thought=thought)

    def agent_finish(self, return_values: dict) -> None:
        self.emit("AGENT_FINISH", return_values=return_values)

    def error(self, error_type: str, message: str, stack: str = None) -> None:
        self.emit("ERROR", level="ERROR", error_type=error_type, message=message, stack=stack)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.error(exc_type.__name__, str(exc_val))
        self.close()
