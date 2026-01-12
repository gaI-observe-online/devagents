from __future__ import annotations

import os
import time

import httpx
import pytest


BASE = "http://localhost:8000"
pytestmark = pytest.mark.integration


def _enabled() -> bool:
    return os.getenv("GADOS_RUN_INTEGRATION_TESTS", "0").strip() == "1"


def _wait_for(url: str, timeout_s: int = 60) -> None:
    if not _enabled():
        pytest.skip("Integration tests disabled (set GADOS_RUN_INTEGRATION_TESTS=1).")
    deadline = time.time() + timeout_s
    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code == 200:
                return
        except Exception as e:  # noqa: BLE001
            last_exc = e
        time.sleep(1)
    raise AssertionError(f"Service did not become ready: {url}. Last error: {last_exc}")


def test_golden_path_creates_report_and_bus_audit_log():
    _wait_for(f"{BASE}/health")

    # 1) Health indicates readiness
    r = httpx.get(f"{BASE}/health", timeout=5.0)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") in {"READY", "ok"}

    # 2) Generate a daily digest report (writes a REPORT-*.md artifact)
    r = httpx.post(f"{BASE}/agents/run/daily-digest", timeout=10.0, follow_redirects=False)
    assert r.status_code in {303, 302}

    # 3) Reports page should list at least one REPORT-
    r = httpx.get(f"{BASE}/reports", timeout=10.0)
    assert r.status_code == 200
    assert "REPORT-" in r.text

    # 4) Emit a bus message and confirm bus audit log is visible as an artifact
    r = httpx.post(
        f"{BASE}/bus/send",
        data={
            "from_role": "CoordinationAgent",
            "from_agent_id": "CA-1",
            "to_role": "CoordinationAgent",
            "to_agent_id": "CA-1",
            "type": "beta.golden_path",
            "severity": "INFO",
            "story_id": "",
            "epic_id": "",
            "notes": "golden-path integration test",
        },
        timeout=10.0,
        follow_redirects=False,
    )
    assert r.status_code in {303, 302}

    r = httpx.get(f"{BASE}/view?path=log/bus/bus-events.jsonl", timeout=10.0)
    assert r.status_code == 200
    assert "MESSAGE_SENT" in r.text

    # 5) Validator endpoint is reachable and returns OK-ish output
    r = httpx.get(f"{BASE}/validate.txt", timeout=10.0)
    assert r.status_code == 200
    assert "OK" in r.text

