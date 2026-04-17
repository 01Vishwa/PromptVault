import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from .span import Span

@dataclass
class Trajectory:
    trajectory_id: str
    run_id: str
    spans: list[Span] = field(default_factory=list)
    final_output: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def step_count(self) -> int:
        return sum(1 for span in self.spans if span.span_type == "CHAIN_STEP")

    @property
    def token_total(self) -> int:
        return sum(
            span.attributes.get("total_tokens", 0)
            for span in self.spans if span.span_type == "LLM_CALL"
        )

    @property
    def duration_ms(self) -> int:
        if not self.spans:
            return 0
        min_start = min(span.start_time for span in self.spans)
        max_end = max(span.end_time for span in self.spans)
        return int((max_end - min_start) * 1000)

    @property
    def tool_names_called(self) -> list[str]:
        tools = [
            span.attributes.get("tool_name")
            for span in self.spans if span.span_type == "TOOL_CALL"
        ]
        return list(set(filter(None, tools)))

    @property
    def error_count(self) -> int:
        return sum(1 for span in self.spans if span.error)

    def step_efficiency_ratio(self, min_steps: int) -> float:
        if self.step_count == 0:
            return 0.0
        return min_steps / self.step_count

    @property
    def trajectory_hash(self) -> str:
        span_data = [span.to_dict() for span in self.spans]
        span_json = json.dumps(span_data, sort_keys=True)
        return hashlib.sha256(span_json.encode("utf-8")).hexdigest()

    def add_span(self, span: Span) -> None:
        self.spans.append(span)

    def to_dict(self) -> dict:
        return {
            "trajectory_id": self.trajectory_id,
            "run_id": self.run_id,
            "spans": [span.to_dict() for span in self.spans],
            "final_output": self.final_output,
            "created_at": self.created_at.isoformat()
        }
