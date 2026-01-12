import os

from fastapi.testclient import TestClient

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from app.main import app  # noqa: E402


def test_healthz():
    client = TestClient(app)
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_track_event():
    client = TestClient(app)
    res = client.post(
        "/track",
        json={"event": "signup_completed", "user_id": "u_1", "properties": {"plan": "pro"}},
    )
    assert res.status_code == 200
    assert res.json() == {"accepted": True}
