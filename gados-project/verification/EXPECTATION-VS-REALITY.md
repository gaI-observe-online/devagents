## Expectation vs Reality: Audit-Grade AI Control Plane (whitepaper artifact)

This document clarifies what the repository is **expected to do** versus what it **actually delivers**, using scenario-based swimlane flow tables to align QA, engineering, and reviewers.

---

## Scenario 1: Daily Spend Guardrail

| Lane | Flow |
|---|---|
| Event Source | Generate Spend Event |
| Economics Engine | Aggregate Spend → Evaluate Budget |
| Policy Gate | Threshold Breach? |
| Control Plane | Emit Trigger → Write Ledger |
| Human | Review Cost Evidence |

---

## Scenario 2: Policy Drift Watchdog

| Lane | Flow |
|---|---|
| Baseline Config | Load Approved Policy |
| Runtime State | Collect Current Config |
| Governance Engine | Compare Baseline vs Current |
| Control Plane | Record Drift Event |
| Human | Review Governance Violation |

---

## Scenario 3: Agent Health & SLA Sentinel

| Lane | Flow |
|---|---|
| Agent | Send Heartbeat |
| Monitor | Measure Latency |
| SLA Engine | Check Threshold |
| Control Plane | Raise Incident |
| Human | Review SLA Breach |

---

## Scenario 4: Code Review & Compliance Audit

| Lane | Flow |
|---|---|
| Code Change | PR / Commit |
| Scanners | SAST → SCA → SBOM → Secrets |
| Specialist IVAs | Analyze Findings |
| Policy Gate | GO / NO-GO |
| Human | Audit Review & Sign-Off |

---

## Scenario 5: Seeded Failure & Recovery

| Lane | Flow |
|---|---|
| Developer | Fix Issue |
| Audit Pipeline | Re-run → GO |
| Policy Gate | NO-GO |

Notes:

- This scenario implies **two runs**:
  - an initial run resulting in **NO-GO** due to a seeded failure
  - a follow-up run after remediation resulting in **GO**

