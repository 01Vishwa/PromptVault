import json
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class Span:
    span_id: str
    trace_id: str
    span_type: str
    start_time: float
    end_time: float
    attributes: dict[str, Any]
    error: bool
    error_message: Optional[str]

    @property
    def duration_ms(self) -> int:
        return int((self.end_time - self.start_time) * 1000)

    @classmethod
    def from_otel(cls, otel_span) -> 'Span':
        return cls(
            span_id=otel_span.get("span_id", ""),
            trace_id=otel_span.get("trace_id", ""),
            span_type=otel_span.get("span_type", "OTHER"),
            start_time=otel_span.get("start_time", 0.0),
            end_time=otel_span.get("end_time", 0.0),
            attributes=otel_span.get("attributes", {}),
            error=otel_span.get("error", False),
            error_message=otel_span.get("error_message")
        )

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "span_type": self.span_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "attributes": self.attributes,
            "error": self.error,
            "error_message": self.error_message
        }
