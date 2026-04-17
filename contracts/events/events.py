from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass
class DomainEvent:
    event_id: UUID
    occurred_at: datetime
    aggregate_id: str

@dataclass
class SpanEmitted(DomainEvent):
    run_id: str
    span_type: str
    attributes: dict

@dataclass
class TaskCompleted(DomainEvent):
    run_id: str
    task_id: str
    status: str
    score: float

@dataclass
class SuiteCompleted(DomainEvent):
    pass_rate: float
    total_tasks: int
    duration_ms: int

@dataclass
class RegressionDetected(DomainEvent):
    task_names: list[str]
    delta: float

@dataclass
class SafetyBreachDetected(DomainEvent):
    run_id: str
    task_id: str
    forbidden_string: str
