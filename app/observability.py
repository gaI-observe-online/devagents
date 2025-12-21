import logging
import os
from contextvars import ContextVar

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pythonjsonlogger import json

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        record.request_id = request_id_ctx.get()  # type: ignore[attr-defined]
        return True


def setup_logging(service_name: str) -> None:
    root = logging.getLogger()
    root.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

    handler = logging.StreamHandler()
    formatter = json.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s "
        "%(request_id)s %(otelTraceID)s %(otelSpanID)s %(otelServiceName)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(_RequestIdFilter())

    root.handlers = [handler]

    # Adds otelTraceID/otelSpanID fields to LogRecord when a span is active.
    LoggingInstrumentor().instrument(set_logging_format=False)

    logging.getLogger(__name__).info("logging_configured", extra={"service_name": service_name})


def setup_observability(service_name: str, otlp_endpoint: str | None = None) -> None:
    """
    Configure OTel traces + metrics exports to an OTLP/HTTP endpoint (default: env).
    """
    if os.getenv("OTEL_SDK_DISABLED", "").lower() in {"1", "true", "yes"}:
        # Useful for unit tests or local runs without a collector.
        setup_logging(service_name=service_name)
        logging.getLogger(__name__).info("otel_sdk_disabled")
        return

    endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")

    resource = Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", service_name),
            "service.version": os.getenv("SERVICE_VERSION", "dev"),
            "deployment.environment": os.getenv("DEPLOYMENT_ENV", "local"),
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")))
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics"),
        export_interval_millis=int(os.getenv("OTEL_METRIC_EXPORT_INTERVAL_MS", "5000")),
    )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

    setup_logging(service_name=service_name)


def instrument_fastapi(app) -> None:
    # Auto-instrument incoming requests with spans.
    FastAPIInstrumentor().instrument_app(app)

