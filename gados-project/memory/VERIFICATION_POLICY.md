## Verification policy (authoritative)

This document defines:

- what “VERIFIED” means
- who can set it
- which evidence is required and how it maps to acceptance criteria
- separation-of-duties (SoD) rules and enforcement points

### Definition of VERIFIED

“VERIFIED” means:

- **acceptance criteria are met**, and are demonstrably supported by evidence
- **evidence is durable** (immutable reference: content hash or write-once artifact ID)
- **independent peer review** occurred and is recorded
- **validation checks** ran and are recorded (CI + any required QA)
- a **VDA decision** is recorded referencing the evidence bundle
- **SoD constraints** are satisfied (implementer ≠ reviewer ≠ VDA, per minimum rules)

### Who can set VERIFIED

Roles:

- **Implementer** (human or agent): produces artifacts; cannot unilaterally set VERIFIED
- **Peer reviewer** (human): reviews changes; records review outcome
- **VDA (Validation Decision Authority)** (human): sets VERIFIED only when policy requirements are met

Minimum rule:

- **VDA must not be the implementer.**

### Evidence requirements (minimum)

Evidence must be attached via immutable references.

- **Peer review record**
  - reviewer identity
  - timestamp
  - decision (`approved | changes_requested | rejected`)
  - notes

- **Validation evidence**
  - CI run IDs + logs (tests, lint, build)
  - QA evidence (manual checklist output or scripted verification output)

- **VDA decision record**
  - decision (`approve | deny | defer`)
  - rationale
  - explicit evidence references relied upon

### Evidence mapping rules (AC → evidence)

For each acceptance criterion (AC):

- **AC must map to at least one evidence item** of one of the following kinds:
  - automated test output (unit/integration/e2e)
  - CI check run (build/lint/security)
  - QA artifact (screenshot, video, manual checklist output)
  - report artifact (compliance report, migration report)

Rules:

- **EM-1 (completeness)**: every AC has ≥1 evidence reference
- **EM-2 (durability)**: every evidence item is immutable (hash or write-once ID)
- **EM-3 (traceability)**: evidence items reference `intent_id`/`correlation_id`
- **EM-4 (reproducibility)**: validation evidence must be re-runnable (commands or CI job definition referenced)

### Separation of duties (SoD)

Rules:

- **SoD-1**: implementer ≠ VDA
- **SoD-2**: peer reviewer ≠ implementer
- **SoD-3 (recommended)**: changes touching governance/audit controls require 2 peer reviewers

### Enforcement points (where policy must be checked)

- **Validator step (preferred)**
  - checks evidence bundle exists and is linked
  - validates SoD constraints from actor identities
  - validates required checks passed
  - blocks VERIFIED if policy is not satisfied

- **CI (minimum automation)**
  - blocks merge/promotion unless required checks succeeded
  - records immutable run IDs/logs as evidence
  - validates required docs artifacts exist

- **Artifact store**
  - enforces write-once or content-addressed artifacts
  - retention policy prevents evidence loss

- **Audit log**
  - append-only records for state transitions, acks/nacks, review and VDA decisions

### Revocation and re-verification

VERIFIED must be revoked if:

- evidence links are broken or altered
- a post-facto defect invalidates acceptance criteria
- SoD violations are discovered

Revocation requires:

- audit log entry describing reason and scope
- re-run lifecycle steps required to restore VALIDATED/VERIFIED with new evidence

