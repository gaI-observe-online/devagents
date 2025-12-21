## Governance specification (authoritative)

This document defines the governance rules for setting and maintaining the **VERIFIED** state.

### Definition of VERIFIED

“VERIFIED” means:

- **Correctness is evidenced**: acceptance criteria are demonstrably met.
- **Evidence is durable**: evidence references are immutable (or content-addressed) and linked from the record.
- **Independent review happened**: peer review was performed by someone other than the implementer.
- **Validation happened**: required automated and/or manual checks were run and recorded.
- **VDA decision recorded**: a designated Validation Decision Authority (VDA) recorded an approve/deny/defer decision referencing evidence.

### Who can set VERIFIED

GADOS requires a separation of duties:

- **Implementer** (human or agent): produces artifacts, cannot unilaterally set VERIFIED.
- **Peer reviewer** (human): performs review and records decision.
- **VDA** (human, role-based): can set VERIFIED **only** when requirements are met.

Minimum rule:

- **The VDA must not be the implementer.**

### Required evidence artifacts (minimum)

- **Peer review record**
  - Reviewer identity
  - Timestamp
  - Review decision and notes
- **Validation evidence**
  - CI run IDs + logs (tests, lint, build)
  - QA evidence (manual checklist output or report artifact)
- **VDA decision record**
  - Decision (approve/deny/defer)
  - Rationale
  - Explicit links to evidence artifacts

### Separation of duties (SoD)

#### Rules

- **SoD-1**: Implementer ≠ VDA
- **SoD-2**: Peer reviewer ≠ Implementer
- **SoD-3**: If a change touches governance or audit controls, require **two** peer reviewers (recommended)

#### Enforcement points (where rules must be checked)

- **Validator step** (preferred):
  - Validates the evidence bundle exists and is linked
  - Confirms actor identities meet SoD constraints
  - Confirms required checks passed
- **CI** (minimum automation):
  - Blocks merge/promotion unless required checks succeeded
  - Records immutable run IDs and logs
- **Artifact store** (durability):
  - Evidence items are write-once (or content-addressed) with retention policy
- **Audit log**:
  - Append-only records for state transitions, acks/nacks, VDA decisions

### Revocation and re-verification

VERIFIED may be revoked if:

- Evidence links are broken or altered
- A post-facto defect invalidates acceptance criteria
- SoD violations are discovered

Revocation requires:

- Audit log entry describing reason and scope
- A new lifecycle run (back to IN_PROGRESS/REVIEWED/VALIDATED as needed)

