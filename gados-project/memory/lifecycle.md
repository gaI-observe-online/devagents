## Lifecycle: INTENT → VERIFIED (authoritative)

This document defines the canonical delivery lifecycle for GADOS and the minimum evidence required to move between states.

### State model

- **INTENT**
  - **Definition**: A human or agent has expressed a problem statement or desired outcome.
  - **Required artifacts**:
    - Intent statement (issue/story text) with scope and non-goals
    - Owner(s) identified

- **PLANNED**
  - **Definition**: The work is decomposed into steps with explicit acceptance criteria and evidence plan.
  - **Required artifacts**:
    - Plan with milestones and dependencies
    - Acceptance criteria (AC)
    - Evidence plan (what will prove AC)
    - Risk notes (security/PII/availability)

- **IN_PROGRESS**
  - **Definition**: Work artifacts are being produced and iterated.
  - **Required artifacts**:
    - Working branch/changeset reference
    - Incremental logs (agent logs / build logs) or progress notes

- **REVIEWED**
  - **Definition**: Another qualified reviewer has performed peer review and recorded outcomes.
  - **Required artifacts**:
    - Peer review record (reviewer identity, timestamp, decision)
    - Review notes addressed or tracked with follow-ups

- **VALIDATED**
  - **Definition**: Validation checks have been run and evidence is attached; VDA decision is recorded.
  - **Required artifacts**:
    - CI/test evidence (logs, reports, checks)
    - QA evidence (manual steps or scripted verification output)
    - Security checks evidence (as applicable)
    - **VDA decision** record (approve/deny/defer) with rationale

- **VERIFIED**
  - **Definition**: Governance requirements are satisfied; the work is accepted as correct and auditable.
  - **Required artifacts**:
    - All VALIDATED evidence preserved and linked
    - Separation-of-duties satisfied (see `governance.md`)
    - Final “VERIFIED” record referencing evidence bundle IDs/paths

### Evidence bundle (recommended structure)

GADOS treats “evidence” as durable, immutable references.

- **Evidence bundle** must include:
  - **Build/test logs**: CI run IDs and links
  - **QA outputs**: screenshots, videos, command outputs, or report artifacts
  - **Peer review**: reviewer identity + notes
  - **VDA decision**: who decided + why + what evidence they relied on

### Allowed transitions (summary)

- INTENT → PLANNED
- PLANNED → IN_PROGRESS
- IN_PROGRESS → REVIEWED (can iterate between IN_PROGRESS and REVIEWED)
- REVIEWED → VALIDATED (can iterate if validation fails)
- VALIDATED → VERIFIED

### Prohibited transitions

- **IN_PROGRESS → VERIFIED** without REVIEWED + VALIDATED evidence
- **VALIDATED → VERIFIED** when separation-of-duties is not satisfied

