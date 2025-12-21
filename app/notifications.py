from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.request import Request, urlopen


Severity = Literal["INFO", "WARN", "ERROR", "CRITICAL"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _runtime_dir() -> Path:
    # Reuse the existing runtime convention
    return Path(os.getenv("GADOS_RUNTIME_DIR", ".gados-runtime")).resolve()


def _queue_path() -> Path:
    return _runtime_dir() / "notifications.queue.jsonl"


def _ensure_runtime_dir() -> None:
    _runtime_dir().mkdir(parents=True, exist_ok=True)


def _severity_rank(sev: Severity) -> int:
    return {"INFO": 10, "WARN": 20, "ERROR": 30, "CRITICAL": 40}[sev]


def _min_webhook_severity() -> Severity:
    v = os.getenv("GADOS_WEBHOOK_MIN_SEVERITY", "CRITICAL").upper().strip()
    return v if v in {"INFO", "WARN", "ERROR", "CRITICAL"} else "CRITICAL"  # type: ignore[return-value]


@dataclass(frozen=True)
class Notification:
    type: str
    severity: Severity
    payload: dict[str, Any]
    story_id: str | None = None
    epic_id: str | None = None
    correlation_id: str | None = None
    artifact_refs: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "gados.notification.v1",
            "at": _utc_now_iso(),
            "type": self.type,
            "severity": self.severity,
            "correlation_id": self.correlation_id,
            "story_id": self.story_id,
            "epic_id": self.epic_id,
            "artifact_refs": self.artifact_refs or [],
            "payload": self.payload,
        }


def dispatch_notification(n: Notification) -> dict[str, Any]:
    """
    Always queues the notification (for daily digest) and optionally dispatches realtime webhook.

    Returns a dict describing what happened, suitable for tests and logging.
    """
    _ensure_runtime_dir()
    doc = n.to_dict()

    # Always queue (append-only)
    with _queue_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps(doc, separators=(",", ":"), ensure_ascii=False) + "\n")

    sent = False
    webhook_url = os.getenv("GADOS_WEBHOOK_URL", "").strip()
    if webhook_url and _severity_rank(n.severity) >= _severity_rank(_min_webhook_severity()):
        body = json.dumps(doc).encode("utf-8")
        req = Request(webhook_url, method="POST", data=body, headers={"Content-Type": "application/json"})

        secret = os.getenv("GADOS_WEBHOOK_HMAC_SECRET", "").encode("utf-8")
        if secret:
            sig = hmac.new(secret, body, hashlib.sha256).hexdigest()
            req.add_header("X-GADOS-Signature", f"sha256={sig}")

        # Best-effort: don't raise to callers; they can check result["sent"].
        try:
            with urlopen(req, timeout=5) as resp:  # noqa: S310
                sent = 200 <= int(getattr(resp, "status", 200)) < 300
        except Exception:
            sent = False

    return {"queued": True, "sent": sent, "queued_path": str(_queue_path())}


def flush_daily_digest(*, output_path: Path, truncate: bool = True) -> dict[str, Any]:
    """
    Convert queued JSONL notifications into a markdown digest artifact.

    - output_path: where to write digest (e.g. gados-project/log/reports/NOTIFICATIONS-YYYYMMDD.md)
    - truncate: if True, clears the queue after flush.
    """
    _ensure_runtime_dir()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not _queue_path().exists():
        output_path.write_text("# Notifications Digest\n\n(no queued notifications)\n", encoding="utf-8")
        return {"flushed": 0, "output_path": str(output_path), "truncated": False}

    lines = _queue_path().read_text(encoding="utf-8").splitlines()
    events: list[dict[str, Any]] = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            events.append(json.loads(ln))
        except Exception:
            # skip malformed lines
            continue

    md: list[str] = []
    md.append("# Notifications Digest")
    md.append("")
    md.append(f"**Generated (UTC)**: {_utc_now_iso()}")
    md.append("")
    if not events:
        md.append("(no queued notifications)")
    else:
        for e in events:
            sev = e.get("severity", "INFO")
            typ = e.get("type", "UNKNOWN")
            story = e.get("story_id")
            when = e.get("at")
            md.append(f"- **{sev}** `{typ}`" + (f" `{story}`" if story else "") + (f" ({when})" if when else ""))
    md.append("")
    output_path.write_text("\n".join(md), encoding="utf-8")

    truncated = False
    if truncate:
        _queue_path().write_text("", encoding="utf-8")
        truncated = True

    return {"flushed": len(events), "output_path": str(output_path), "truncated": truncated}

