from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GADOS_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.delenv("GADOS_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("GADOS_WEBHOOK_HMAC_SECRET", raising=False)
    monkeypatch.delenv("GADOS_WEBHOOK_MIN_SEVERITY", raising=False)


def test_dispatch_queues_and_does_not_send_without_webhook():
    from app.notifications import Notification, dispatch_notification

    res = dispatch_notification(Notification(type="TEST", severity="CRITICAL", payload={"a": 1}))
    assert res["queued"] is True
    assert res["sent"] is False

    queue_path = Path(res["queued_path"])
    assert queue_path.exists()
    assert queue_path.read_text(encoding="utf-8").strip() != ""


def test_realtime_gating_by_severity(monkeypatch: pytest.MonkeyPatch):
    from app.notifications import Notification, dispatch_notification

    monkeypatch.setenv("GADOS_WEBHOOK_URL", "http://example.invalid/webhook")
    monkeypatch.setenv("GADOS_WEBHOOK_MIN_SEVERITY", "CRITICAL")

    # WARN should not attempt realtime sending
    res = dispatch_notification(Notification(type="TEST", severity="WARN", payload={}))
    assert res["queued"] is True
    assert res["sent"] is False


def test_flush_daily_digest_truncates_queue(tmp_path: Path):
    from app.notifications import Notification, dispatch_notification, flush_daily_digest

    dispatch_notification(Notification(type="A", severity="INFO", payload={}))
    dispatch_notification(Notification(type="B", severity="ERROR", payload={}))

    out_path = tmp_path / "digest.md"
    res = flush_daily_digest(output_path=out_path, truncate=True)
    assert res["flushed"] == 2
    assert res["truncated"] is True
    assert out_path.exists()
    assert "Notifications Digest" in out_path.read_text(encoding="utf-8")

    # Queue should be cleared
    runtime_dir = Path(tmp_path / "runtime")
    queue_path = runtime_dir / "notifications.queue.jsonl"
    assert queue_path.exists()
    assert queue_path.read_text(encoding="utf-8") == ""

