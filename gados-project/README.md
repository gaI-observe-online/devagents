# GADOS — Governance & Audit Delivery Operating System

GADOS is a lightweight governance system for agent-assisted software delivery. It turns human/agent **intent** into **audit-ready artifacts** and a **VERIFIED** decision backed by evidence (tests, QA outputs, peer review, validation decision authority).

This repository’s GADOS docs are intentionally split into:

- **Memory (authoritative)**: rules/specs/runbooks that define “what is true” for audits and enforcement.
- **Strategy (narrative)**: architecture explanations and diagrams that explain “how it works”.

## Repo layout (GADOS docs)

To keep merges and audits clean, the core GADOS docs are stored as **versioned artifacts**:

- `gados-project/strategy/ARCHITECTURE.md` (Mermaid blocks inside)
- `gados-project/strategy/RUNBOOKS.md` (local dev, test env, CI, observability)
- `gados-project/memory/COMM_PROTOCOL.md`
- `gados-project/memory/NOTIFICATION_POLICY.md`
- `gados-project/memory/VERIFICATION_POLICY.md`
- `gados-project/memory/ui-screenshots-checklist.md` (optional audit checklist)

## Collaboration (shared place)

For ongoing status updates, handoffs, and decisions, use:

- `gados-project/collaboration/STATUS.md`
- `gados-project/collaboration/HANDOFF.md`
- `gados-project/collaboration/DECISIONS.md`

## Intent → VERIFIED lifecycle (one page)

The lifecycle is enforced by the verification policy:

- `gados-project/memory/VERIFICATION_POLICY.md` (authoritative)

At a high level, lifecycle states are:

- **INTENT**: a story/problem statement exists (human or agent)
- **PLANNED**: explicit plan + acceptance criteria + evidence plan
- **IN_PROGRESS**: artifacts being produced (code, reports, diffs, logs)
- **REVIEWED**: peer review recorded, issues addressed
- **VALIDATED**: validation checks run; evidence is attached; VDA decision recorded
- **VERIFIED**: governance rules satisfied; final state set by permitted actor(s)

## Authoritative memory files (audit references)

- `gados-project/memory/VERIFICATION_POLICY.md`
- `gados-project/memory/COMM_PROTOCOL.md`
- `gados-project/memory/NOTIFICATION_POLICY.md`
- `gados-project/memory/ui-screenshots-checklist.md`

