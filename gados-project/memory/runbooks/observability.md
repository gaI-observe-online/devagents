## Runbook: Observability (authoritative)

This runbook defines how to confirm GADOS telemetry in Grafana (Tempo/Loki/Mimir).

### Preconditions

- You have Grafana access (self-hosted or SaaS).
- OpenTelemetry export is enabled for the control-plane service.
- `service.name` is set to `gados-control-plane` (or your chosen canonical name).

### Tempo (traces) — confirm traces exist

In **Explore → Traces (Tempo)**:

- **Search**:
  - `service.name = "gados-control-plane"`
  - Time range: last 15 minutes
- **Expected**:
  - Spans for API requests and agent-bus operations
  - Correlated trace IDs show in logs (when log correlation is enabled)

### Loki (logs) — confirm structured logs exist

In **Explore → Logs (Loki)**:

- Query examples:
  - `{service_name="gados-control-plane"} |= "status_changed"`
  - `{service_name="gados-control-plane"} |= "audit"`
- Expected log fields:
  - `request_id`
  - `otelTraceID`, `otelSpanID`
  - `message` with stable event names (e.g. `audit.append`, `bus.ack`)

### Mimir/Prometheus (metrics) — confirm metrics exist

In **Explore → Metrics**:

- Useful queries:
  - `sum(rate(analytics_events_total[5m])) by (event_name)`
  - `sum(rate(http_server_request_duration_seconds_count[5m])) by (service_name)` (if available)
- Expected:
  - Non-zero rates during activity
  - Labels include `service_name` or equivalent resource attributes

### Minimal verification procedure

- Trigger a known operation (e.g. create intent → plan → status change).
- Capture:
  - A trace URL (Tempo)
  - A log query + representative log lines (Loki)
  - A metric query + graph screenshot (Mimir)
- Store these as validation artifacts and link them in the evidence bundle.

