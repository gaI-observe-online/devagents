## Architecture narrative (strategy)

This document explains the high-level architecture of GADOS and how it supports audit-ready delivery.

### Core idea

GADOS is a **control-plane** that coordinates:

- intents and lifecycle state transitions
- agent work (planner/implementer/validator)
- artifact storage (evidence)
- governance enforcement (SoD, required checks)
- observability (logs/metrics/traces)

### Major components (conceptual)

- **CA GUI**
  - Human interface for creating intents, viewing status, inbox, artifacts, and validation decisions.

- **Control-plane**
  - Orchestrates lifecycle transitions, enforces governance rules, and routes work to agents and CI.

- **Agent bus**
  - Message transport for agent-to-agent and control-plane coordination (durable queue + inbox semantics).

- **Artifact store**
  - Durable storage for evidence bundles (reports, logs, screenshots, diffs) with immutable references.

- **CI / Validator**
  - Automated validation producing evidence and status updates.

- **Observability stack (LGTM/Grafana)**
  - Stores traces (Tempo), logs (Loki), metrics (Mimir) and provides query UX (Grafana).

### Audit-ready properties

- **Traceability**: every decision references evidence IDs and audit log entries.
- **Immutability**: evidence artifacts are content-addressed or write-once.
- **SoD enforcement**: VERIFIED requires independent peer review and VDA approval.
- **Reproducibility**: validation can be re-run; outputs are preserved.

### Authoritative specifications

The rules that matter for audits are in:

- `gados-project/memory/lifecycle.md`
- `gados-project/memory/governance.md`
- `gados-project/memory/protocol/agent-message-types.md`
- `gados-project/memory/protocol/notification-policy.md`

