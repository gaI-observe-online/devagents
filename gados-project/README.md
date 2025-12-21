# GADOS Project

**GADOS** (Governed Agentic Delivery Operating System) is an artifact-governed delivery system where AI speed is preserved while **truth, auditability, separation of duties, and economic control** are enforced.

## Cardinal rule
**If it's not in an artifact, it doesn't exist.** AI memory is ephemeral; artifacts are versioned, auditable, and authoritative.

## What this repository contains
This folder is the **system of record** for delivery governance:

- **Authoritative memory**: `/gados-project/memory/` (vision, principles, guardrails)
- **Strategic plans (epics)**: `/gados-project/strategy/`
- **Plan artifacts**: `/gados-project/plan/` (epics, stories, approved change plans)
- **Audit logs**: `/gados-project/log/` (append-only delivery trail)
- **Decisions**: `/gados-project/decision/` (human authority escalations)
- **Verification**: `/gados-project/verification/` (evidence + peer review packages)

## Lifecycle (intent → truth)
Typical story states:

- `PLANNED`
- `IN_PROGRESS`
- `IMPLEMENTED`
- `QA_EVIDENCE_READY`
- `PEER_REVIEWED`
- `VERIFIED` (**only Delivery Governor / VDA can advance to this**)
- `RELEASED`
- `ESCALATED`

## Roles (separation of powers)
- **Human Authority**: vision, ethics, escalation approval, irreversible/economic decisions.
- **Strategic Brain**: epic framing, architecture & economics recommendations (no code, no verification).
- **Coordination Agent (CA)**: control plane, artifact routing, memory management, reporting (no strategy, no code, no verification).
- **Delivery Governor (VDA)**: verification authority, acceptance criteria enforcement, certify truth (no code, no pricing).
- **Execution Engine (Vibe)**: implement approved changes + tests within bounds (no scope changes, no self-verification).

## Getting started
1. Write/update foundational artifacts in `/gados-project/memory/`.
2. Create an epic in `/gados-project/strategy/` and its metadata in `/gados-project/plan/epics/`.
3. Create a story spec in `/gados-project/plan/stories/`.
4. Create an approved change plan in `/gados-project/plan/changes/` (must be VDA-approved to execute).
5. Append delivery events to `/gados-project/log/STORY-XXX.log.yaml`.
6. Collect evidence and peer review in `/gados-project/verification/`.
7. Record any escalations in `/gados-project/decision/`.

