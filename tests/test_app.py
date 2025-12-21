from __future__ import annotations

from fastapi.testclient import TestClient


def test_example_app_endpoints(monkeypatch):
    # Disable OTel SDK for tests (no collector required).
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")

    from app.main import app

    c = TestClient(app)
    r = c.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    r2 = c.get("/")
    assert r2.status_code == 200
    assert r2.json()["hello"] == "world"

    r3 = c.post("/track", json={"event": "signup_completed", "user_id": "u_1", "properties": {"plan": "pro"}})
    assert r3.status_code == 200
    assert r3.json()["accepted"] is True

