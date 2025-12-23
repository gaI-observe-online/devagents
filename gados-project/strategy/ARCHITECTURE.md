## GADOS architecture (versioned artifact)

This document is the high-level architecture narrative for GADOS and includes the authoritative Mermaid architecture/sequence diagrams used for reviews and audits.

### Overview

GADOS is a lightweight governance system for agent-assisted software delivery. It turns human/agent **intent** into **audit-ready artifacts** and a **VERIFIED** decision backed by evidence (tests, QA outputs, peer review, VDA decision).

Conceptually, GADOS is a **control-plane** that coordinates:

- intents and lifecycle state transitions
- agent work (planner/implementer/validator)
- artifact storage (evidence bundles)
- governance enforcement (separation-of-duties, required checks)
- observability (logs/metrics/traces)

### Major components (conceptual)

- **CA GUI**
  - Human UI for intents, inbox, artifacts, and validation decisions.
- **Control-plane**
  - Orchestrates lifecycle transitions, enforces governance rules, and routes work to agents and CI.
- **Agent bus**
  - Message transport (durable queue + inbox semantics).
- **Artifact store**
  - Durable store for evidence bundles with immutable references (hashes / write-once IDs).
- **CI / Validator**
  - Automated validation producing evidence and status updates.
- **Observability stack (LGTM/Grafana)**
  - Stores traces (Tempo), logs (Loki), metrics (Mimir) and provides query UX (Grafana).

### Audit-ready properties

- **Traceability**: every decision references evidence IDs and audit log entries.
- **Immutability**: evidence artifacts are content-addressed or write-once.
- **Separation of duties**: VERIFIED requires independent peer review and VDA approval.
- **Reproducibility**: validation can be re-run; outputs are preserved.

---

## Mermaid diagrams

### C4 Context

```mermaid
C4Context
title GADOS - C4 Context

Person(human, "Human", "Creates intents, reviews, and approves VERIFIED.")
System(ca_gui, "CA GUI", "Human UI for intents, inbox, artifacts, validation.")
System(control_plane, "GADOS Control-plane", "Orchestrates lifecycle, governance, routing.")
System(langgraph_agents, "LangGraph Agents", "Planner/Implementer/Validator agents.")
System(git_artifacts, "Git Artifacts", "Branches, diffs, PRs, CI runs, logs.")
System(lgtm, "LGTM / Grafana", "Observability: Tempo/Loki/Mimir + Grafana UI.")

Rel(human, ca_gui, "Uses")
Rel(ca_gui, control_plane, "Creates intents; views status; triggers validation")
Rel(control_plane, langgraph_agents, "Dispatches work via agent bus")
Rel(langgraph_agents, git_artifacts, "Reads/writes code; produces diffs; triggers CI")
Rel(control_plane, git_artifacts, "Reads CI status; stores references to evidence")
Rel(control_plane, lgtm, "Emits traces/metrics/logs (OTel)")
Rel(ca_gui, lgtm, "Links to logs/traces/metrics during validation")
```

### C4 Container

```mermaid
C4Container
title GADOS - C4 Container

Person(human, "Human", "Operator / reviewer / VDA")

System_Boundary(gados, "GADOS") {
  Container(ca_gui, "CA GUI", "Web UI", "Dashboard, Inbox, Artifacts, Validate")
  Container(control_plane, "Control-plane", "Service", "Lifecycle orchestration + governance engine")
  Container(agent_bus, "Agent bus", "Messaging", "Send/receive, durable queue, inbox semantics")
  ContainerDb(artifact_store, "Artifact store", "Object store", "Evidence bundles (immutable refs)")
  Container(ci, "CI", "Automation", "Build/test/lint; produces validation evidence")
  Container(audit_log, "Audit log", "Append-only store", "State transitions, acks/nacks, VDA decisions")
}

System_Ext(git, "Git hosting", "Repo + PRs + checks")
System_Ext(lgtm, "LGTM / Grafana", "Tempo/Loki/Mimir + Grafana")

Rel(human, ca_gui, "Uses")
Rel(ca_gui, control_plane, "HTTP/JSON")
Rel(control_plane, agent_bus, "Publishes/consumes messages")
Rel(agent_bus, audit_log, "Appends send/ack/nack events")
Rel(control_plane, artifact_store, "Writes evidence refs")
Rel(ci, artifact_store, "Writes reports/logs artifacts")
Rel(control_plane, ci, "Requests validations; reads results")
Rel(control_plane, git, "Reads commits/PR/checks")
Rel(control_plane, lgtm, "Exports OTel telemetry")
Rel(ci, lgtm, "Exports job telemetry")
```

### Sequence: Story lifecycle (PLANNED → … → VERIFIED)

```mermaid
sequenceDiagram
autonumber
participant H as Human
participant UI as CA GUI
participant CP as Control-plane
participant AG as LangGraph Agents
participant CI as CI/Validator
participant AS as Artifact Store
participant AL as Audit Log
participant VDA as VDA (Human)

H->>UI: Create/confirm INTENT (intent_id)
UI->>CP: intent.created
CP->>AL: audit.append (intent created)

H->>UI: Confirm plan + AC + evidence plan
UI->>CP: plan.created
CP->>AL: audit.append (state=PLANNED)
CP->>AS: artifact.created (plan artifact + hash)

CP->>AG: work.started (dispatch implementer)
AG->>AS: artifact.created (diffs/reports as produced)
AG->>CI: validation.requested (tests/lint)
CI->>AS: artifact.created (test logs + reports)
CI->>CP: validation.completed (pass/fail + evidence refs)
CP->>AL: audit.append (state=VALIDATED or remediation required)

CP->>UI: request peer review
H->>UI: Peer review recorded (approve/changes)
UI->>CP: review.recorded
CP->>AL: audit.append (state=REVIEWED)

CP->>UI: Present evidence bundle + validation results
VDA->>UI: Approve/deny/defer with rationale
UI->>CP: vda.decision.recorded
CP->>AL: audit.append (VDA decision)

alt All governance rules satisfied
  CP->>AL: audit.append (state=VERIFIED + evidence refs)
  CP->>UI: Show VERIFIED badge + links to evidence
else Missing evidence / SoD violation / failed checks
  CP->>UI: Block VERIFIED; show required remediation
  CP->>AL: audit.append (verification blocked)
end
```

### Sequence: Agent bus delivery (send → durable queue → inbox → ack/nack → audit log)

```mermaid
sequenceDiagram
autonumber
participant P as Producer (Agent/CP)
participant Q as Durable Queue
participant IB as Consumer Inbox
participant C as Consumer (Agent/CP)
participant AL as Audit Log

P->>Q: send(message_id, type, correlation_id)
Q->>AL: audit.append(bus.send)
Q->>IB: deliver(message)
IB->>C: notify/inbox item available

alt Processed successfully
  C->>Q: ack(message_id)
  Q->>AL: audit.append(bus.ack)
else Processing failed (retryable)
  C->>Q: nack(message_id, error, retryable=true)
  Q->>AL: audit.append(bus.nack)
  Q-->>IB: redeliver with backoff
else Processing failed (non-retryable)
  C->>Q: nack(message_id, error, retryable=false)
  Q->>AL: audit.append(bus.nack)
  Q->>AL: audit.append(notification.escalate)
end
```

