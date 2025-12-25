import os
import signal
import subprocess
import time

import httpx


def _wait_for_ok(url: str, timeout_s: int = 20) -> None:
    deadline = time.time() + timeout_s
    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=1.0)
            if r.status_code == 200:
                return
        except Exception as e:  # noqa: BLE001
            last_exc = e
        time.sleep(0.2)
    raise AssertionError(f"Service did not become ready: {url}. Last error: {last_exc}")


def test_local_smoke_without_docker():
    """
    Alternative to Docker-based integration:
    - starts the API locally
    - checks /health
    - posts /track
    - terminates the server
    """
    port = 8001
    base = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    env["OTEL_SDK_DISABLED"] = "true"

    proc = subprocess.Popen(  # noqa: S603
        ["python3", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for_ok(f"{base}/health", timeout_s=20)

        r = httpx.get(f"{base}/health", timeout=5.0)
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

        r = httpx.post(
            f"{base}/track",
            json={"event": "qa_smoke", "user_id": "qa", "properties": {"mode": "nodocker"}},
            timeout=5.0,
        )
        assert r.status_code == 200
        assert r.json() == {"accepted": True}
    finally:
        # Try graceful shutdown, then force if needed.
        if proc.poll() is None:
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        # If it crashed, surface logs for debugging.
        if proc.returncode not in (0, None):
            out = (proc.stdout.read() if proc.stdout else "")[:5000]
            raise AssertionError(f"uvicorn failed rc={proc.returncode}\n{out}")


def test_docker_compose_has_expected_ports():
    """
    Alternative evidence when Docker isn't available:
    verify the compose file still exposes the required ports.
    """
    text = open("docker-compose.yml", encoding="utf-8").read()  # noqa: PTH123
    assert "grafana/otel-lgtm" in text
    assert "3000:3000" in text
    assert "4318:4318" in text
