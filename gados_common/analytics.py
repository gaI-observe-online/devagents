from __future__ import annotations

import hashlib
import logging
import os
import re
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
_redactions_counter = _meter.create_counter(
    name="analytics_redactions_total",
    description="Count of redacted analytics fields/values",
    unit="1",
)


_DEFAULT_ALLOWLIST = {
    "scenario",
    "decision",
    "run_id",
    "run_key",
    "story_id",
    "epic_id",
    "status",
    "severity",
    "component",
    "route",
    "method",
    "http_status",
    "correlation_id",
}

_SUSPECT_KEY_RE = re.compile(
    r"(pass(word)?|secret|token|api[_-]?key|auth(orization)?|cookie|session|jwt|bearer|credit|card|pan|cvv|ssn|email|phone)",
    re.IGNORECASE,
)
_JWT_RE = re.compile(r"^[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}$")
_STRIPE_SK_RE = re.compile(r"\bsk_(live|test)_[A-Za-z0-9]{10,}\b", re.IGNORECASE)


def _allowlist() -> set[str]:
    raw = os.getenv("GADOS_ANALYTICS_PROPERTIES_ALLOWLIST", "").strip()
    if not raw:
        return set(_DEFAULT_ALLOWLIST)
    items = [p.strip() for p in raw.split(",") if p.strip()]
    if not items:
        return set(_DEFAULT_ALLOWLIST)
    return set(items)


def _hash_user_id(user_id: str) -> str:
    # Stable, irreversible identifier for correlation without PII leakage.
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16]


def _is_jsonish_primitive(v: Any) -> bool:
    return v is None or isinstance(v, (str, int, float, bool))


def _coerce_jsonish(v: Any) -> Any:
    if _is_jsonish_primitive(v):
        return v
    if isinstance(v, (list, tuple)):
        return [_coerce_jsonish(x) for x in v[:50]]
    if isinstance(v, dict):
        out: dict[str, Any] = {}
        for k, val in list(v.items())[:50]:
            out[str(k)] = _coerce_jsonish(val)
        return out
    return str(v)


def _looks_like_secret_value(v: Any) -> bool:
    if not isinstance(v, str):
        return False
    s = v.strip()
    if not s:
        return False
    if _JWT_RE.match(s):
        return True
    if _STRIPE_SK_RE.search(s):
        return True
    # Very long opaque blobs are likely tokens/keys.
    return len(s) >= 80


def _scrub_properties(props: Mapping[str, Any]) -> tuple[dict[str, Any], int]:
    """
    Allowlist keys and redact likely secrets/PII. Returns (safe_props, redactions_count).
    """
    allow = _allowlist()
    safe: dict[str, Any] = {}
    redactions = 0

    for k, v in (props or {}).items():
        key = str(k)
        if key not in allow:
            redactions += 1
            continue

        # Key-based redaction
        if _SUSPECT_KEY_RE.search(key) is not None:
            safe[key] = "<redacted>"
            redactions += 1
            continue

        # Value-based redaction
        vv = _coerce_jsonish(v)
        if _looks_like_secret_value(vv):
            safe[key] = "<redacted>"
            redactions += 1
            continue

        safe[key] = vv

    return safe, redactions


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
    safe_props, redactions = _scrub_properties(properties or {})
    attrs_log: dict[str, Any] = {"event_name": event}
    if user_id:
        attrs_log["user_id_hash"] = _hash_user_id(user_id)
    if safe_props:
        attrs_log["properties"] = safe_props

    _events_counter.add(1, attributes={"event_name": event})
    if redactions:
        _redactions_counter.add(redactions, attributes={"event_name": event})

    span = trace.get_current_span()
    if span is not None:
        # OTel span attributes must be primitives (or lists of primitives).
        attrs_otel: dict[str, Any] = {"event_name": event}
        if user_id:
            attrs_otel["user_id_hash"] = _hash_user_id(user_id)
        for i, (k, v) in enumerate(safe_props.items()):
            if i >= 25:
                break
            attrs_otel[f"prop.{k}"] = v if _is_jsonish_primitive(v) else str(v)
        if redactions:
            attrs_otel["redactions"] = int(redactions)
        span.add_event("analytics.event", attributes=attrs_otel)

    _log.info("analytics_event", extra=attrs_log)

