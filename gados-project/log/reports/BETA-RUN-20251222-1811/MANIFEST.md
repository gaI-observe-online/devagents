# Beta run manifest

**Run ID**: BETA-RUN-20251222-1811
**Date (UTC)**: 2025-12-22

## Scenario 1 — Daily Spend Guardrail
- Artifacts:
  - `01-daily-spend-guardrail/ESCALATION-001.md`
  - `01-daily-spend-guardrail/ledger.jsonl`

## Scenario 2 — Policy Drift Watchdog
- Artifacts:
  - `02-policy-drift-watchdog/POLICY-DRIFT-20251222-181146.md`

## Scenario 3 — Agent Health & SLA Breach Sentinel
- Artifacts:
  - `03-sla-sentinel/SLA-BREACH-20251222-181147.md`

## Scenario 4 — Code Review Factory
- Artifacts (folder):
  - `04-code-review-factory/review-pack/`

## Scenario 5 — Offline Audit Graph (LangGraph)
- Artifacts (folder):
  - `05-offline-audit-graph/audit-pack/`

## Shared runtime/audit snapshots
- `shared/notifications.queue.jsonl` (queued notifications at end of run)
- `shared/NOTIFICATIONS-20251222.md` (digest artifact)
- `shared/bus-events.jsonl` (append-only bus audit log snapshot)
