from __future__ import annotations

import os
import time

import httpx
import pytest


BASE = "http://localhost:8000"

pytestmark = pytest.mark.integration


def _wait_for(url: str, timeout_s: int = 60) -> None:
    if os.getenv("GADOS_RUN_INTEGRATION_TESTS", "0").strip() != "1":
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


def test_health_ok():
    _wait_for(f"{BASE}/health")
    r = httpx.get(f"{BASE}/health", timeout=5.0)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_root_ok():
    _wait_for(f"{BASE}/health")
    r = httpx.get(f"{BASE}/", timeout=5.0)
    assert r.status_code == 200


def test_reports_ok():
    _wait_for(f"{BASE}/health")
    r = httpx.get(f"{BASE}/reports", timeout=5.0)
    assert r.status_code == 200

