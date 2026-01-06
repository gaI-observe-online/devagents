# Beta scenarios — verification & validation (5 runs)

This is the **copy/paste runbook** to execute the 5 beta scenarios and review their evidence artifacts.

## Preconditions
- From repo root
- Python env installed:
  - `make install`
- Docker **not required** for beta (per decision); optional for docker smoke.

## Run folder convention (recommended)
Create a folder per run and copy artifacts into it:

`gados-project/log/reports/BETA-RUN-YYYYMMDD-HHMM/`

Include a `MANIFEST.md` listing the scenario outputs and their paths.

## Scenario 1 — Daily Spend Guardrail (economics threshold loop)
**Command**
```bash
make beta-guardrail
```

**Expected evidence**
- `gados-project/log/economics/ledger.jsonl` appended
- `gados-project/decision/ESCALATION-###.md` created
- Bus audit log appended: `gados-project/log/bus/bus-events.jsonl`
- Notification queued: `.gados-runtime/notifications.queue.jsonl`

**Review**
- Open the escalation decision file and confirm it references correlation/scope and budget facts.
- Check `bus-events.jsonl` contains `MESSAGE_SENT` with `type=economics.budget_threshold`.

## Scenario 2 — Policy Drift Watchdog (baseline vs runtime config)
**Command (force drift)**
```bash
GADOS_RATE_LIMIT_RPS=999 make beta-policy-drift
```

**Expected evidence**
- Drift report created: `gados-project/log/reports/POLICY-DRIFT-*.md`
- Bus audit log appended: `gados-project/log/bus/bus-events.jsonl`
- Notification queued: `.gados-runtime/notifications.queue.jsonl`

**Review**
- Confirm report lists drifted keys and severity.
- Confirm bus audit log contains `type=policy.drift_detected`.

## Scenario 3 — Agent Health & SLA Breach Sentinel
**Command (expected breach if no heartbeat recorded)**
```bash
make beta-sla
```

**Expected evidence**
- Incident report created: `gados-project/log/reports/SLA-BREACH-*.md`
- Bus audit log appended: `gados-project/log/bus/bus-events.jsonl`
- Notification queued: `.gados-runtime/notifications.queue.jsonl`

**Optional “healthy” check**
```bash
PYTHONPATH=. .venv/bin/python scripts/run_sla_sentinel.py --beat-first
```

## Scenario 4 — Code Review Factory (audit-ready review pack)
**Command (local)**
```bash
REVIEW_PACK_DIR=review-pack python scripts/generate_review_pack.py || true
```

**Expected evidence**
- Folder created: `review-pack/`
- Includes:
  - `Executive_Summary.md` (GO/NO-GO)
  - `Findings.csv`
  - `SAST_Report.json`, `SCA_Report.json`, `SBOM.cyclonedx.json`, `Secrets_Report.json`
  - `Evidence/` raw outputs
  - `SHA256SUMS.txt` (optional traceability)

**Review**
- Start with `Executive_Summary.md`, then open `Findings.csv`.

## Scenario 5 — Offline Audit Graph (LangGraph, tool-first, no LLM)
**Command**
```bash
make beta-audit-graph
```

**Expected evidence**
- Folder created: `audit_run_local/audit-pack/`
- Includes:
  - `Executive_Summary.md`
  - `Findings_Register.csv`
  - `Control_Matrix.csv`
  - `Tool_Outputs/` (raw JSON outputs)
  - `SHA256SUMS.txt` (optional traceability)

## Final step — Digest evidence
**Command**
```bash
make notify-digest-flush
```

**Expected evidence**
- `gados-project/log/reports/NOTIFICATIONS-YYYYMMDD.md`

