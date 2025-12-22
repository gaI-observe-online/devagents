# Collaboration Guidelines (How to Work in This Repo)

Use this hub to keep delivery **auditable**, **merge-clean**, and **governed**.

## Where to write what
- **Status (edit in place)**: `STATUS.md`
  - Current workstream state + blockers + QA snapshot.
- **Handoffs (append-only)**: `HANDOFF.md`
  - Every meaningful delivery/handoff must be appended with verification evidence.
- **Decisions (append-only)**: `DECISIONS.md`
  - Human Authority decisions and architecture decisions (or links to ADR/ESCALATION artifacts).

## Evidence standard (required)
If you claim “done”, include **verbatim command outputs** (or CI links) in the handoff:
- `python3 -m ruff check .`
- `python3 -m pytest -q`
- `python3 gados-control-plane/scripts/validate_artifacts.py`
- If Docker is used: `make test-env-up && make test-smoke && make test-integration && make test-env-down`

## Merge-clean rules
- Prefer **append-only** logs for handoffs/decisions (avoid conflicts).
- Keep `STATUS.md` short; don’t paste long logs there—link to evidence artifacts instead.
- Never create competing “authoritative” docs. If a doc is superseded, update references and remove duplicates.

## Observability tightening (expected deliverables)
When working on observability, the minimum “tightening” set is:
- **PII/secret scrubbing** for analytics properties (allowlist/redact) + tests
- **Trace sampling** (env-controlled) + documented defaults
- **Grafana Cloud clickpath** doc:
  - where to find OTLP endpoint + token
  - 2–3 Explore queries for Tempo/Loki/Mimir
- Optional: **dashboard JSON** (requests, errors, p95, analytics_events_total)

## Observability evidence (what to prove)
Provide a small evidence note (can live in a handoff entry) showing:
- A trace exists in Tempo for `service.name="gados-control-plane"` (or `example-api`)
- Logs correlate (trace/span IDs present)
- A metric exists (e.g., `gados_debug_trace_total` or `analytics_events_total`)

## Safety note
Even on VPN/local: do not disable auth in deployed environments. Set `GADOS_BASIC_AUTH_USER/PASSWORD`.

