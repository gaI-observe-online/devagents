## Beta scenarios (authoritative) — execution checklist (inputs → expectations → evidence)

This file turns the 5 beta scenarios into **run steps + evidence capture requirements**.  
For each scenario, record results in `gados-project/verification/BETA-QA-evidence.md` (or link a dedicated file under `gados-project/verification/`).

Swimlane summary reference:

- `gados-project/verification/EXPECTATION-VS-REALITY.md`

---

## Scenario 1 — Daily Spend Guardrail (Economics Control)

### Inputs
- A set of `LedgerEntry` spend events (category/vendor mix)
- A budget (USD) that will be crossed

### Expectations
- Spend is ingested and aggregated
- Threshold evaluation returns `WARN/HIGH/CRITICAL/HARD_STOP`
- A trigger event is produced
- Evidence is written (ledger line + escalation doc) and alert/message emitted

### Evidence (minimum)
- Verbatim test output showing threshold reached (unit or integration)
- Ledger artifact:
  - `gados-project/log/economics/ledger.jsonl` (or other agreed path)
- Escalation artifact:
  - `gados-project/decision/ESCALATION-<id>.md`
- Notification/bus evidence:
  - bus audit log line(s) or notification report

### Current repo status
- **Implemented**: economics threshold trigger builder (`app/economics.build_budget_trigger_event`)
- **Not yet end-to-end** (in this branch): trigger → ledger/escalation/bus wiring (owned by validator/economics agent branch)

---

## Scenario 2 — Policy Drift Watchdog (Governance Control)

### Inputs
- An approved baseline policy config snapshot (hashable artifact)
- A deliberate policy/config drift (edit, delete, or add a rule)

### Expectations
- Drift is detected vs baseline
- Violation is logged with evidence
- Human review is requested if policy impact is ambiguous

### Evidence (minimum)
- Baseline artifact reference + hash
- Drift diff (verbatim)
- Governance violation report artifact (path + contents)
- Audit log entry recording drift detection + action taken

### Current repo status
- **Not yet implemented end-to-end** in this branch (requires baseline store + diff + reporting).

---

## Scenario 3 — Agent Health & SLA Sentinel (Reliability Control)

### Inputs
- Heartbeat events (on-time)
- Missed heartbeat or SLA breach (deliberate)

### Expectations
- Heartbeats monitored
- SLA breach raises alert
- Failure is traceable and auditable
- Observability links exist (logs/trace IDs)

### Evidence (minimum)
- Heartbeat log lines (verbatim)
- SLA breach alert artifact or message
- Audit record with timestamps
- Observability proof (logs/traces) or links

### Current repo status
- **Partial**: CI integration smoke generates telemetry; local Docker is blocked here.
- **Not yet implemented**: heartbeat/SLA subsystem and incident record artifacts.

---

## Scenario 4 — Code Review & Security Audit (Compliance Control)

### Inputs
- A codebase/PR with defined changes (preferably e-commerce sample)
- Deterministic scanners configured (secrets/SAST/SCA/SBOM)
- IVA playbooks (PCI/Checkout, Security/OWASP, Privacy)

### Expectations
- Scanners run deterministically and outputs are preserved
- IVAs analyze tool outputs and map findings (OWASP/CWE/PCI readiness)
- Coordinator dedupes and enforces policy gates
- Audit evidence pack generated:
  - exec summary + findings register + raw outputs + signoff template

### Evidence (minimum)
- `audit-pack/` directory listing (verbatim)
- `00_Executive_Summary.md` includes GO/NO-GO + counts + evidence references
- `03_Findings_Register.(json/csv)` matches tool outputs
- Raw tool outputs saved under `audit-pack/Tool_Outputs/`
- `06_Reviewer_Signoff.md` present

### Current repo status
- **Planning artifacts exist**: `BETA-REGRESSION-PLAN.md`, `BETA-EVIDENCE-PACK-CHECKLIST.md`
- **Not yet implemented end-to-end**: deterministic scanner pipeline + IVA playbooks + audit-pack generator.

---

## Scenario 5 — Seeded Failure & Recovery (Audit Credibility Test)

### Inputs
- Seeded failure (e.g., hardcoded secret / known vulnerable dep / missing auth check)
- A follow-up commit fixing the issue

### Expectations
- Seeded failure run produces NO-GO with evidence
- Fix run produces GO with evidence
- Repeatability: same inputs yield same decision/finding set

### Evidence (minimum)
- Two runs (FAIL then FIX) with:
  - executive summaries (NO-GO then GO)
  - findings register showing removed finding
  - raw tool output proving the finding existed then cleared
- Determinism proof:
  - rerun of one state matches (or identical findings hash)

### Current repo status
- **Depends on Scenario 4 tooling**; not yet end-to-end in this branch.

