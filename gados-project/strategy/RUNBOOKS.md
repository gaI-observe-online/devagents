## GADOS runbooks (versioned artifact)

This file consolidates operational runbooks for consistent execution and auditability.

---

## Local dev

### Preconditions

- You can access the **Dashboard** (CA GUI).
- You can access the **Inbox** (tasks/messages).
- You can access the **Artifacts** view (evidence and reports).

### Start dashboard

- Open the Dashboard (CA GUI).
- Confirm you can see:
  - recent intents
  - items by lifecycle state
  - alerts/notifications summary

### Run reports

- From “Reports”:
  - run “Lifecycle compliance” report (states and missing evidence)
  - run “SoD compliance” report (implementer/reviewer/VDA separation)
  - export the report as an artifact

### Use inbox

- Open “Inbox”.
- For a selected `intent_id`:
  - accept assignment (creates an audit log record)
  - follow the plan and update status (INTENT → PLANNED → …)
  - attach artifacts to the intent:
    - plan, diffs, test outputs, QA evidence, review notes

### Validate governance (before requesting VERIFIED)

Use:

- `gados-project/memory/VERIFICATION_POLICY.md`

Checklist:

- peer review exists and is linked
- validation evidence exists and is linked
- VDA decision exists and is linked
- separation-of-duties rules satisfied

---

## Test environment

### Bring up the test environment

Run:

```bash
make test-env-up
```

Expected:

- environment endpoints are reachable
- a run ID (or deployment ID) is printed and stored as an artifact

### Run smoke tests

Run:

```bash
make test-smoke
```

Required evidence:

- command output stored as an artifact
- any screenshots/videos stored as artifacts

### Run full test suite

Run:

```bash
make test
```

Required evidence:

- CI run ID or local run logs preserved
- test report artifacts attached (JUnit/coverage if applicable)

### If any step fails

- record failure details as an artifact (logs, screenshots)
- do not request VERIFIED until failures are resolved and re-validated

---

## CI

### What CI must do (minimum)

- install dependencies
- run lint
- run tests
- fail fast on missing required docs artifacts

### Required docs artifacts check

CI must verify the following files exist:

- `gados-project/strategy/ARCHITECTURE.md`
- `gados-project/strategy/RUNBOOKS.md`
- `gados-project/memory/COMM_PROTOCOL.md`
- `gados-project/memory/NOTIFICATION_POLICY.md`
- `gados-project/memory/VERIFICATION_POLICY.md`

---

## Observability

### Tempo (traces) — confirm traces exist

In **Explore → Traces (Tempo)**:

- search: `service.name = "gados-control-plane"`
- time range: last 15 minutes
- expected:
  - spans for API requests and agent-bus operations
  - trace IDs correlate into logs (if log correlation enabled)

### Loki (logs) — confirm structured logs exist

In **Explore → Logs (Loki)**:

- query examples:
  - `{service_name="gados-control-plane"} |= "status_changed"`
  - `{service_name="gados-control-plane"} |= "audit"`
- expected log fields:
  - `request_id`
  - `otelTraceID`, `otelSpanID`

### Mimir/Prometheus (metrics) — confirm metrics exist

In **Explore → Metrics**:

- query examples:
  - `sum(rate(analytics_events_total[5m])) by (event_name)`
- expected:
  - non-zero rates during activity

### Minimal verification procedure

- trigger a known operation (create intent → plan → status change)
- capture:
  - a trace URL (Tempo)
  - a log query + representative log lines (Loki)
  - a metric query + graph screenshot (Mimir)
- store these as validation artifacts and link them in the evidence bundle

