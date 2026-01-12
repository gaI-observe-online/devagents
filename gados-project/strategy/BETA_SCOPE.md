# Beta scope (freeze)

This document declares what “beta” means for this repo right now: **in-scope**, **out-of-scope**, and the **acceptance gates** required to call it “beta”.

## Assumed beta definition
- **Internal beta**
- **Single-user / small team**, local-first
- **Docker optional** (required only for observability + docker smoke profile)

## In scope (beta)
- Control-plane UI is runnable locally and exposes `/health`.
- Governance artifacts exist and validator runs in CI.
- Agent bus provides durable messaging (SQLite queue) + append-only audit log (JSONL).
- Notifications queue + digest flush tooling works locally (webhook optional).
- Economics ledger supports append-only JSONL entries + threshold evaluation + trigger payloads.
- Baseline security knobs: optional basic auth, explicit CORS policy, request size cap, basic rate limiting, auth failure audit logging.

## Out of scope (beta)
- Multi-tenant auth/RBAC and per-user identity management.
- Production-grade distributed rate limiting.
- Production persistence guarantees across clustered deployments (beyond “single host”).
- Full webhook/channel integrations (Slack/email/etc.) beyond generic webhook.

## Beta acceptance gates (must pass)

### A) Golden path start/stop
- `cp .env.example .env`
- `make up` succeeds and `make verify` returns OK.
- `make down` stops the server cleanly.

### B) Quality + governance
- `python3 -m ruff check .` **PASS**
- `python3 -m pytest -q` **PASS**
- `python3 gados-control-plane/scripts/validate_artifacts.py` **PASS**

### C) Workflow gates enforcement (governance tightening)
Per `gados-project/memory/WORKFLOW_GATES.md`:
- Validator enforces required artifacts/log events for `IMPLEMENTED+` and `VERIFIED/RELEASED` stories.
- Unit tests prove pass/fail for each rule.

### D) Economics trigger wiring
- Runtime writes valid JSONL lines to `gados-project/log/economics/ledger.jsonl`.
- On threshold breach: create an `decision/ESCALATION-###.md` (or ADR) and send a bus/notification event.
- Unit tests prove trigger→action behavior.

### E) QA evidence package
- `gados-project/verification/BETA-QA-evidence.md` is filled with verbatim command outputs and a PASS/FAIL.
- `make notify-digest-flush` produces `gados-project/log/reports/NOTIFICATIONS-YYYYMMDD.md` (referenced in evidence).

## Optional (nice-to-have)
- If Docker is available: `make test-docker` passes and Tempo traces are visible in Grafana for `service.name="gados-control-plane"`.

