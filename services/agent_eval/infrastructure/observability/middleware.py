from typing import Any, Dict, List
import time
from langchain.callbacks.base import BaseCallbackHandler
from .tracer import OTelTracer
from .logger import StructuredLogger
from ...domain.entities.span import Span
from ...domain.entities.trajectory import Trajectory
from ...domain.events.domain_events import EventBus
from contracts.events.events import SpanEmitted, TaskCompleted
from uuid import uuid4
from datetime import datetime

class TrajectoryCollector:
    """Accumulates spans during a run, builds Trajectory domain entity."""
    def __init__(self, run_id: str, task_id: str, min_steps: int = 1):
        self.run_id = run_id
        self.task_id = task_id
        self.min_steps = min_steps
        self.spans: List[Span] = []
        self.final_output = ""

    def record_llm(self, span: Span, tokens_total: int, tokens_prompt: int, tokens_completion: int) -> None:
        span.attributes["tokens_total"] = tokens_total
        span.attributes["tokens_prompt"] = tokens_prompt
        span.attributes["tokens_completion"] = tokens_completion
        self.spans.append(span)

    def record_tool(self, span_or_none: Span | None, tool_name: str, error: bool) -> None:
        if span_or_none:
            span_or_none.attributes["tool_name"] = tool_name
            span_or_none.error = error
            self.spans.append(span_or_none)

    def set_final_output(self, output: str) -> None:
        self.final_output = output

    def build(self, status: str) -> Trajectory:
        return Trajectory(
            trajectory_id=str(uuid4()),
            run_id=self.run_id,
            spans=self.spans,
            final_output=self.final_output
        )

    async def save(self, run_repo, traj_repo, status: str) -> Trajectory:
        trajectory = self.build(status)
        await traj_repo.save(trajectory, self.run_id)
        return trajectory


def _safe_hook(func):
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            self.logger.error("CallbackError", str(e))
    return wrapper

class HarnessCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback: transparent capture of all agent events.
    Emits OTel spans, structured logs, and domain events.
    NEVER raises — all hooks wrapped in _safe_hook().
    """
    def __init__(self, run_id: str, logger: StructuredLogger,
                 collector: TrajectoryCollector, event_bus: EventBus):
        self.run_id = run_id
        self.logger = logger
        self.collector = collector
        self.event_bus = event_bus
        self._spans: Dict[str, Span] = {}

    def _start_span(self, key: str, name: str, **attrs) -> Span:
        span_id = OTelTracer.current_span_id()
        trace_id = OTelTracer.current_trace_id()
        if span_id == "no-span":
            span_id = str(uuid4())
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            span_type=name,
            start_time=time.time(),
            end_time=0.0,
            attributes=attrs,
            error=False,
            error_message=None
        )
        self._spans[key] = span
        return span

    def _end_span(self, key: str, **attrs) -> Span | None:
        span = self._spans.pop(key, None)
        if span:
            span.end_time = time.time()
            span.attributes.update(attrs)
            # Emit DomainEvent
            try:
                self.event_bus.publish(SpanEmitted(
                    event_id=uuid4(),
                    occurred_at=datetime.utcnow(),
                    aggregate_id=self.run_id,
                    run_id=self.run_id,
                    span_type=span.span_type,
                    attributes=span.attributes
                ))
            except Exception:
                pass
        return span

    @_safe_hook
    def on_llm_start(self, serialized, prompts, **kwargs):
        run_id_llm = str(kwargs.get("run_id", uuid4()))
        self._start_span(run_id_llm, "LLM_CALL")
        self.logger.llm_start("unknown_model", str(prompts)[:100])

    @_safe_hook
    def on_llm_end(self, response, **kwargs):
        run_id_llm = str(kwargs.get("run_id", ""))
        span = self._end_span(run_id_llm)
        usage = response.llm_output.get("usage", {}) if response.llm_output else {}
        tt = usage.get("total_tokens", 0)
        tp = usage.get("prompt_tokens", 0)
        tc = usage.get("completion_tokens", 0)
        if span:
            self.collector.record_llm(span, tt, tp, tc)
        self.logger.llm_end(tt, tp, tc, str(response.generations)[:100])

    @_safe_hook
    def on_llm_error(self, error: BaseException, **kwargs):
        run_id_llm = str(kwargs.get("run_id", ""))
        span = self._spans.get(run_id_llm)
        if span:
            span.error = True
            span.error_message = str(error)
            span = self._end_span(run_id_llm)
        self.logger.error("LLMError", str(error))

    @_safe_hook
    def on_tool_start(self, serialized, input_str, **kwargs):
        run_id_tool = str(kwargs.get("run_id", uuid4()))
        tool_name = serialized.get("name", "unknown") if serialized else "unknown"
        self._start_span(run_id_tool, "TOOL_CALL", tool_name=tool_name)
        self.logger.tool_start(tool_name, input_str)

    @_safe_hook
    def on_tool_end(self, output, **kwargs):
        run_id_tool = str(kwargs.get("run_id", ""))
        span = self._end_span(run_id_tool)
        tool_name = span.attributes.get("tool_name", "unknown") if span else "unknown"
        self.collector.record_tool(span, tool_name, error=False)
        self.logger.tool_end(tool_name, str(output)[:100], len(str(output)))

    @_safe_hook
    def on_tool_error(self, error: BaseException, **kwargs):
        run_id_tool = str(kwargs.get("run_id", ""))
        span = self._spans.get(run_id_tool)
        tool_name = span.attributes.get("tool_name", "unknown") if span else "unknown"
        if span:
            span.error = True
            span.error_message = str(error)
            span = self._end_span(run_id_tool)
        self.collector.record_tool(span, tool_name, error=True)
        self.logger.error("ToolError", str(error))

    @_safe_hook
    def on_chain_start(self, serialized, inputs, **kwargs):
        run_id_chain = str(kwargs.get("run_id", uuid4()))
        self._start_span(run_id_chain, "CHAIN_STEP")

    @_safe_hook
    def on_chain_end(self, outputs, **kwargs):
        run_id_chain = str(kwargs.get("run_id", ""))
        span = self._end_span(run_id_chain)
        if span:
            self.collector.spans.append(span)

    @_safe_hook
    def on_agent_action(self, action, **kwargs):
        self.logger.agent_action(action.tool, str(action.tool_input), action.log)

    @_safe_hook
    def on_agent_finish(self, finish, **kwargs):
        self.logger.agent_finish(finish.return_values)
        self.collector.set_final_output(str(finish.return_values))
        try:
            self.event_bus.publish(TaskCompleted(
                event_id=uuid4(),
                occurred_at=datetime.utcnow(),
                aggregate_id=self.run_id,
                run_id=self.run_id,
                task_id=self.collector.task_id,
                status="PASS",
                score=0.0
            ))
        except Exception:
            pass
