# GADOS Runbooks

This document is the **single runbook** for local dev, testing, CI, and observability verification.

## Local development (control plane)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e gados-control-plane
uvicorn gados_control_plane.main:app --reload --port 8000
```

Open:
- Dashboard: `http://localhost:8000/`
- Reports: `http://localhost:8000/reports`
- Inbox (agent bus): `http://localhost:8000/inbox`
- Validation: `http://localhost:8000/validate`

## Local observability (LGTM via Docker)

Start LGTM:

```bash
docker compose -f compose.test.yml up -d lgtm
```

Run control plane locally against LGTM:

```bash
export OTEL_SERVICE_NAME=gados-control-plane
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
uvicorn gados_control_plane.main:app --reload --port 8000
```

## Local test environment (LGTM + control-plane in Docker)

```bash
make test-env-up
```

Health checks:

```bash
curl -fsS http://localhost:3000/api/health
curl -fsS http://localhost:8000/health
```

Generate smoke traffic:

```bash
make test-smoke
```

Run tests:

```bash
make test
```

Tear down:

```bash
make test-env-down
```

## CI
CI runs:
- docker compose test env up
- waits for `http://localhost:8000/health`
- smoke traffic generation
- `ruff` + `pytest`
- governance validation

Workflow: `.github/workflows/ci.yml`

## Verify traces in Grafana (2 steps)
1. Open Grafana: `http://localhost:3000` → **Explore** → select **Tempo**.
2. Query for traces from the service: filter on `service.name="gados-control-plane"` and open any trace.

Tip: hit `http://localhost:8000/debug/trace` to force a deterministic span + metric + log line.

