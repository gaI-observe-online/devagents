# Grafana Cloud (Free) — OTLP “clickpath” + Explore queries

This is the **lowest-friction** way to send traces/metrics from GADOS to Grafana Cloud **without Docker**.

## 1) Create the free stack
- In Grafana Cloud, create a **Free** stack.

## 2) Find your OTLP endpoint + auth (UI clickpath)
- Go to **Connections** → **OpenTelemetry**
- Choose **OTLP (HTTP)** (not gRPC)
- Copy:
  - **Endpoint** (looks like `https://otlp-gateway-<region>.grafana.net/otlp`)
  - **Headers** (Grafana shows an `Authorization=Basic ...` value)

## 3) Set env vars (copy/paste)

In your `.env` (or shell), set:

```bash
OTEL_SDK_DISABLED=0
OTEL_EXPORTER_OTLP_ENDPOINT="https://<your-otlp-endpoint>"
OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <paste-from-grafana>"
OTEL_SERVICE_NAME="gados-control-plane"
DEPLOYMENT_ENV="beta"

# Sampling (recommended for free tier)
GADOS_TRACE_SAMPLE_RATIO=0.25
```

Notes:
- `OTEL_EXPORTER_OTLP_ENDPOINT` is the **base**; the code uses `/v1/traces` and `/v1/metrics`.
- If you prefer standard vars, you can instead use:
  - `OTEL_TRACES_SAMPLER=parentbased_traceidratio`
  - `OTEL_TRACES_SAMPLER_ARG=0.25`

## 4) Confirm data is arriving (Explore)

### Tempo (Traces)
- Go to **Explore** → select **Tempo**
- Query (TraceQL):

```text
{ resource.service.name = "gados-control-plane" }
```

If you don’t see traces:
- Hit `http://127.0.0.1:8000/debug/trace` a few times
- Refresh Explore

### Mimir / Prometheus (Metrics)
- Go to **Explore** → select **Prometheus**
- Queries:

```text
analytics_events_total
```

```text
sum by (event_name) (analytics_events_total)
```

If FastAPI HTTP server metrics are available from auto-instrumentation, you can also search:
- Start typing `http_` and use autocomplete.

### Loki (Logs)
This repo currently emits **structured JSON logs to stdout** and adds `otelTraceID/otelSpanID` fields for correlation.

To view logs in Grafana Cloud Loki you need an **agent** (Grafana Alloy / Promtail) to ship stdout/file logs to Loki.

Once logs are shipped, use Loki Explore with a label selector like:

```text
{service_name="gados-control-plane"}
```

And then filter for correlated traces by searching the JSON field:
- `otelTraceID="<trace_id_here>"`

