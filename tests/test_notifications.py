import json
from pathlib import Path

import pytest

from app.notifications import NotificationEvent, dispatch_notification, flush_daily_digest


def test_non_critical_queued_to_digest(monkeypatch, tmp_path: Path):
    digest_path = tmp_path / "digest.jsonl"
    monkeypatch.setenv("GADOS_NOTIFICATIONS_ENABLED", "true")
    monkeypatch.setenv("GADOS_DAILY_DIGEST_ENABLED", "true")
    monkeypatch.setenv("GADOS_CRITICAL_REALTIME_ENABLED", "true")
    monkeypatch.setenv("GADOS_DIGEST_STORE_PATH", str(digest_path))
    monkeypatch.delenv("GADOS_WEBHOOK_URL", raising=False)

    res = dispatch_notification(NotificationEvent(event_type="test.event", priority="high", summary="hi"))
    assert res == "queued_digest"
    assert digest_path.exists()
    lines = digest_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["schema"] == "gados.digest.queue.v1"
    assert payload["event"]["event_type"] == "test.event"


def test_critical_requires_webhook(monkeypatch, tmp_path: Path):
    digest_path = tmp_path / "digest.jsonl"
    monkeypatch.setenv("GADOS_NOTIFICATIONS_ENABLED", "true")
    monkeypatch.setenv("GADOS_DAILY_DIGEST_ENABLED", "true")
    monkeypatch.setenv("GADOS_CRITICAL_REALTIME_ENABLED", "true")
    monkeypatch.setenv("GADOS_DIGEST_STORE_PATH", str(digest_path))
    monkeypatch.delenv("GADOS_WEBHOOK_URL", raising=False)

    res = dispatch_notification(NotificationEvent(event_type="test.critical", priority="critical"))
    assert res == "dropped"


def test_flush_daily_digest_posts_and_truncates(monkeypatch, tmp_path: Path):
    digest_path = tmp_path / "digest.jsonl"
    digest_path.write_text(
        "\n".join(
            [
                json.dumps({"schema": "gados.digest.queue.v1", "event": {"event_type": "a"}}),
                json.dumps({"schema": "gados.digest.queue.v1", "event": {"event_type": "b"}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    calls: list[dict] = []

    def fake_post(url: str, payload: dict, secret=None):  # noqa: ANN001
        calls.append({"url": url, "payload": payload, "secret": secret})

    monkeypatch.setattr("app.notifications._webhook_post", fake_post)

    sent = flush_daily_digest(webhook_url="https://example.invalid/webhook", store_path=str(digest_path))
    assert sent == 2
    assert calls[0]["payload"]["class"] == "daily_digest"
    assert calls[0]["payload"]["event_type"] == "gados.daily_digest"
    assert digest_path.read_text(encoding="utf-8") == ""


def test_notifications_can_be_disabled(monkeypatch):
    monkeypatch.setenv("GADOS_NOTIFICATIONS_ENABLED", "false")
    res = dispatch_notification(NotificationEvent(event_type="test.event"))
    assert res == "dropped"


def test_digest_can_be_disabled(monkeypatch, tmp_path: Path):
    digest_path = tmp_path / "digest.jsonl"
    monkeypatch.setenv("GADOS_NOTIFICATIONS_ENABLED", "true")
    monkeypatch.setenv("GADOS_DAILY_DIGEST_ENABLED", "false")
    monkeypatch.setenv("GADOS_DIGEST_STORE_PATH", str(digest_path))
    monkeypatch.delenv("GADOS_WEBHOOK_URL", raising=False)

    res = dispatch_notification(NotificationEvent(event_type="test.event", priority="high"))
    assert res == "dropped"
    assert not digest_path.exists()


def test_critical_can_be_forced_to_digest(monkeypatch, tmp_path: Path):
    digest_path = tmp_path / "digest.jsonl"
    monkeypatch.setenv("GADOS_NOTIFICATIONS_ENABLED", "true")
    monkeypatch.setenv("GADOS_DAILY_DIGEST_ENABLED", "true")
    monkeypatch.setenv("GADOS_CRITICAL_REALTIME_ENABLED", "false")
    monkeypatch.setenv("GADOS_DIGEST_STORE_PATH", str(digest_path))

    res = dispatch_notification(NotificationEvent(event_type="test.critical", priority="critical"))
    assert res == "queued_digest"
    assert digest_path.exists()


@pytest.mark.parametrize("value,expected", [("true", True), ("1", True), ("yes", True), ("false", False), ("0", False)])
def test_env_bool_parsing(monkeypatch, value, expected):  # noqa: ANN001
    monkeypatch.setenv("GADOS_NOTIFICATIONS_ENABLED", value)
    res = dispatch_notification(NotificationEvent(event_type="test.event"))
    assert (res != "dropped") is expected

