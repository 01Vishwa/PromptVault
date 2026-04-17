import contextlib
import logging
import uuid
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

class OTelTracer:
    """Singleton OTel tracer wrapper."""
    _instance = None
    _tracer = None

    @classmethod
    def initialise(cls, service_name: str, endpoint: str) -> None:
        if cls._instance is None:
            resource = Resource.create({
                "service.name": service_name,
                "deployment.environment": "development"
            })
            provider = TracerProvider(resource=resource)
            exporter = OTLPSpanExporter(endpoint=endpoint)
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)
            cls._tracer = trace.get_tracer(service_name)
            cls._instance = cls()

    @classmethod
    def get(cls) -> trace.Tracer:
        if cls._tracer is None:
            cls.initialise("eval-core-fallback", "http://localhost:4317")
        return cls._tracer

    @staticmethod
    def current_trace_id() -> str:
        span = trace.get_current_span()
        if span.get_span_context().is_valid:
            return format(span.get_span_context().trace_id, "032x")
        return "no-trace"

    @staticmethod
    def current_span_id() -> str:
        span = trace.get_current_span()
        if span.get_span_context().is_valid:
            return format(span.get_span_context().span_id, "016x")
        return "no-span"

    @staticmethod
    @contextlib.contextmanager
    def span(name: str, attributes: dict = None):
        with OTelTracer.get().start_as_current_span(name) as s:
            if attributes:
                s.set_attributes(attributes)
            try:
                yield s
            except Exception as e:
                s.record_exception(e)
                s.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise

if __name__ == "__main__":
    OTelTracer.initialise("smoke-test", "http://localhost:4317")
    with OTelTracer.span("smoke", {"test": True}):
        print("Tracer OK")
