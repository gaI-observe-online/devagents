# GADOS — Governance & Audit Delivery Operating System

GADOS is a lightweight governance system for agent-assisted software delivery. It turns human/agent **intent** into **audit-ready artifacts** and a **VERIFIED** decision backed by evidence (tests, QA outputs, peer review, validation decision authority).

This repository’s GADOS docs are intentionally split into:

- **Memory (authoritative)**: rules/specs/runbooks that define “what is true” for audits and enforcement.
- **Strategy (narrative)**: architecture explanations and diagrams that explain “how it works”.

## Repo layout (GADOS docs)

- `gados-project/memory/`
  - `lifecycle.md`: lifecycle states and the **intent → VERIFIED** contract
  - `governance.md`: definition of VERIFIED + separation-of-duties enforcement points
  - `protocol/`
    - `agent-message-types.md`: agent-to-agent message catalog (schemas + escalation)
    - `notification-policy.md`: critical realtime vs digest policy, channels, rate limits
  - `runbooks/`
    - `local-dev.md`: local dev workflow (dashboard, reports, inbox, governance validation)
    - `test-env.md`: test environment workflow (`make test-env-up/test-smoke/test`)
    - `observability.md`: Grafana Explore queries (Tempo/Loki/Mimir) and verification steps
  - `ui-screenshots-checklist.md`: optional audit checklist for required UI pages
- `gados-project/strategy/`
  - `architecture.md`: high-level architecture narrative
  - `diagrams.md`: Mermaid diagrams (C4 + sequences)

## Intent → VERIFIED lifecycle (one page)

The authoritative lifecycle is defined in:

- `gados-project/memory/lifecycle.md` (authoritative)

At a high level:

- **INTENT**: a story/problem statement exists (human or agent)
- **PLANNED**: explicit plan + acceptance criteria + evidence plan
- **IN_PROGRESS**: artifacts being produced (code, reports, diffs, logs)
- **REVIEWED**: peer review recorded, issues addressed
- **VALIDATED**: validation checks run; evidence is attached; VDA decision recorded
- **VERIFIED**: governance rules satisfied; final state set by permitted actor(s)

## Authoritative memory files (audit references)

- `gados-project/memory/lifecycle.md`
- `gados-project/memory/governance.md`
- `gados-project/memory/protocol/agent-message-types.md`
- `gados-project/memory/protocol/notification-policy.md`
- `gados-project/memory/runbooks/local-dev.md`
- `gados-project/memory/runbooks/test-env.md`
- `gados-project/memory/runbooks/observability.md`
- `gados-project/memory/ui-screenshots-checklist.md`

