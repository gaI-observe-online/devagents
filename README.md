# GADOS DevAgents

This repository contains:

- **GADOS artifact memory + governance**: `gados-project/`
- **Interactive dashboard + reporting + LangGraph agents**: `gados-control-plane/`
- **Local observability stack (free)**: `docker-compose.yml` (Grafana LGTM: logs/traces/metrics)

## Quick start

### 1) Run the local observability stack (optional, free)

```bash
docker compose up -d
```

Grafana: `http://localhost:3000`  
OTLP HTTP endpoint: `http://localhost:4318`

### 2) Run the GADOS control plane dashboard

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export OTEL_SERVICE_NAME=gados-control-plane
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

uvicorn gados_control_plane.main:app --reload --port 8000
```

Open: `http://localhost:8000`

## Reports (LangGraph virtual agents)
In the UI, open **Reports** and run the “daily digest” agent graph.
It writes an audit-friendly report artifact to `gados-project/log/reports/`.

## Strategic game plan (HTML)
Open this file in a browser:
- `gados-project/strategy/GADOS-STRATEGIC-GAME-PLAN.html`

