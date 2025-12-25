import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class NotificationEvent:
    """
    A small, stable event envelope for outbound notifications.

    This is intentionally not coupled to any UI. It is designed to be produced by
    control-plane/validator/CI components and consumed by webhook receivers.
    """

    event_type: str
    priority: str = "normal"  # low|normal|high|critical
    summary: str = ""
    correlation_id: str | None = None
    subject_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    occurred_at: float = field(default_factory=lambda: time.time())


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _hmac_signature(secret: str, body: bytes) -> str:
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def _webhook_post(url: str, payload: dict[str, Any], secret: str | None = None) -> None:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-GADOS-Signature"] = _hmac_signature(secret, body)

    req = urllib.request.Request(url=url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            # Read response to release connection; ignore contents.
            resp.read()
    except urllib.error.HTTPError as e:  # pragma: no cover (depends on remote)
        raise RuntimeError(f"webhook_http_error status={e.code}") from e
    except urllib.error.URLError as e:  # pragma: no cover (depends on remote)
        raise RuntimeError("webhook_url_error") from e


def enqueue_digest_event(event: NotificationEvent, *, store_path: str) -> None:
    """
    Append a digest event into a JSONL queue.

    Queue semantics are intentionally simple: append-only; a daily job can ship
    and then truncate/rotate.
    """
    record = {
        "schema": "gados.digest.queue.v1",
        "event": asdict(event),
    }
    os.makedirs(os.path.dirname(store_path) or ".", exist_ok=True)
    with open(store_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":"), sort_keys=True))
        f.write("\n")


def flush_daily_digest(*, webhook_url: str, store_path: str, secret: str | None = None) -> int:
    """
    Ship all queued digest events as one webhook payload and truncate the queue.

    Returns the number of queued events shipped.
    """
    if not os.path.exists(store_path):
        return 0

    events: list[dict[str, Any]] = []
    with open(store_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # Skip malformed lines; production should quarantine and alert.
                continue

    if not events:
        return 0

    payload = {
        "schema": "gados.notification.v1",
        "class": "daily_digest",
        "event_type": "gados.daily_digest",
        "priority": "normal",
        "summary": "GADOS daily digest",
        "details": {"events": events},
    }
    _webhook_post(webhook_url, payload, secret=secret)

    # Truncate after successful send.
    with open(store_path, "w", encoding="utf-8"):
        pass
    return len(events)


def dispatch_notification(event: NotificationEvent) -> str:
    """
    Reference behavior implementing `gados-project/memory/NOTIFICATION_POLICY.md`.

    - Critical realtime: priority=critical -> send webhook immediately.
    - Daily digest: everything else -> enqueue for daily digest.

    Returns: "sent_realtime" | "queued_digest" | "dropped"
    """
    enabled = _bool_env("GADOS_NOTIFICATIONS_ENABLED", True)
    if not enabled:
        return "dropped"

    webhook_url = os.getenv("GADOS_WEBHOOK_URL", "").strip()
    secret = os.getenv("GADOS_WEBHOOK_SECRET")
    digest_path = os.getenv("GADOS_DIGEST_STORE_PATH", "/tmp/gados_digest.jsonl")

    critical_enabled = _bool_env("GADOS_CRITICAL_REALTIME_ENABLED", True)
    digest_enabled = _bool_env("GADOS_DAILY_DIGEST_ENABLED", True)

    if event.priority == "critical" and critical_enabled:
        if not webhook_url:
            return "dropped"
        payload = {
            "schema": "gados.notification.v1",
            "class": "critical_realtime",
            "event_type": event.event_type,
            "priority": event.priority,
            "correlation_id": event.correlation_id,
            "subject_id": event.subject_id,
            "summary": event.summary,
            "details": event.details,
        }
        _webhook_post(webhook_url, payload, secret=secret)
        return "sent_realtime"

    if digest_enabled:
        enqueue_digest_event(event, store_path=digest_path)
        return "queued_digest"

    return "dropped"
