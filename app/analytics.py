import logging
from collections.abc import Mapping
from typing import Any

from opentelemetry import metrics, trace

_log = logging.getLogger(__name__)
_meter = metrics.get_meter("analytics")
_events_counter = _meter.create_counter(
    name="analytics_events_total",
    description="Count of tracked analytics events",
    unit="1",
)


def track_event(
    event: str,
    *,
    user_id: str | None = None,
    properties: Mapping[str, Any] | None = None,
) -> None:
    """
    Minimal analytics wrapper:
    - increments a counter (event_name label)
    - adds a span event if a span is active
    - emits a structured log line
    """
    props = dict(properties or {})
    attrs: dict[str, Any] = {"event_name": event}
    if user_id:
        attrs["user_id"] = user_id
    if props:
        # Keep attributes flat for common backends; store props as one field.
        attrs["properties"] = props

    _events_counter.add(1, attributes={"event_name": event})

    span = trace.get_current_span()
    if span is not None:
        span.add_event("analytics.event", attributes=attrs)

    _log.info("analytics_event", extra=attrs)

