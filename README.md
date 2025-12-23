# Analytics & Observability Starter Kit

This repo provides a minimal, working baseline for:

- **Observability**: structured logs + distributed traces + metrics via **OpenTelemetry**
- **Analytics**: a simple `track_event()` wrapper that records product events as telemetry (metrics + trace events + logs)
- **Local stack**: a single Docker container that runs Grafana + Tempo (traces) + Loki (logs) + Mimir (metrics) + an OTel Collector

## Quick start (local)

### 1) Start the local observability stack

```bash
docker compose up -d
```

Grafana will be available at `http://localhost:3000`.

### 2) Run the example service

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export OTEL_SERVICE_NAME=example-api
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3) Generate some traffic (and an analytics event)

```bash
curl -s http://localhost:8000/healthz

curl -s -X POST http://localhost:8000/track \
  -H 'content-type: application/json' \
  -d '{"event":"signup_completed","user_id":"u_123","properties":{"plan":"pro"}}'
```

## What you get

- **Traces**:
  - inbound HTTP requests are automatically traced
  - `POST /track` adds a span event (`analytics.event`)
- **Metrics**:
  - `analytics_events_total{event_name="..."}` counter emitted via OTel
- **Logs**:
  - JSON logs including `request_id`, `otelTraceID`, `otelSpanID`

## How to adopt in a real app

- Copy `app/observability.py` + `app/analytics.py` into your service and call `setup_observability()` once on startup.
- Keep `track_event()` as the single entry point for product analytics so you can later swap the sink (PostHog/Segment/Snowplow/etc.) without touching business code.

## Quick start (SaaS, free tier)

### Grafana Cloud Free (recommended)

1) Create a free Grafana Cloud stack and open **OpenTelemetry / OTLP** settings.

2) Set these environment variables for the API:

```bash
export OTEL_SERVICE_NAME=example-api
export DEPLOYMENT_ENV=dev

# Use the OTLP HTTP endpoint provided by Grafana Cloud, typically ending with /otlp
export OTEL_EXPORTER_OTLP_ENDPOINT="https://<your-grafana-cloud-otlp-endpoint>"

# Set the auth header exactly as Grafana Cloud tells you (usually Basic auth).
# Format: "Authorization=Basic <token>"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <your-token>"
```

3) Run the service and generate traffic (same as local).

