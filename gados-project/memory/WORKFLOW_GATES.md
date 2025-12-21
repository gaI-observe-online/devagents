## Workflow gates: state machine + required artifacts (authoritative artifact)

This document defines the **exact lifecycle state machine** and the **required artifacts per transition**, and how a validator should enforce it.

### Canonical states

- **INTENT**
- **PLANNED**
- **IN_PROGRESS**
- **REVIEWED**
- **VALIDATED**
- **VERIFIED**

Optional terminal states (implementation-specific):

- **REJECTED** (explicit deny)
- **CANCELLED**

### Actors

- **Implementer**: produces work artifacts (human or agent)
- **Peer reviewer**: independent reviewer (human)
- **VDA**: Validation Decision Authority (human)
- **Validator**: automated enforcement (CI job / service)

---

## State machine (exact transitions)

### Allowed transitions

| From | To | Trigger event | Who can trigger | Notes |
|---|---|---|---|---|
| (none) | INTENT | `intent.created` | Human / CA GUI | Creates intent record |
| INTENT | PLANNED | `plan.created` | Implementer/Planner | Requires acceptance criteria + evidence plan |
| PLANNED | IN_PROGRESS | `work.started` | Implementer/Agent | Records branch/work reference |
| IN_PROGRESS | REVIEWED | `review.recorded` | Peer reviewer | Review decision must be recorded |
| REVIEWED | IN_PROGRESS | `review.recorded` | Peer reviewer | If `changes_requested` |
| REVIEWED | VALIDATED | `validation.completed` | CI/Validator | Validation must be green and evidence attached |
| VALIDATED | VERIFIED | `vda.decision.recorded` | VDA | Enforced by validator gate |
| ANY | CANCELLED | `intent.cancelled` | Human/VDA | Must include rationale |
| ANY | REJECTED | `vda.decision.recorded` | VDA | If `deny` |

### Prohibited transitions (hard fail)

- IN_PROGRESS → VERIFIED
- PLANNED → VERIFIED
- REVIEWED → VERIFIED
- VALIDATED → VERIFIED without VDA decision
- VERIFIED → (anything) without explicit revocation workflow (out of scope here)

---

## Required artifacts per transition

Artifacts are referenced by immutable IDs (content hash or write-once artifact IDs).

### INTENT → PLANNED (`plan.created`)

Required:

- **Plan artifact** (`artifact.kind = plan.v1`)
  - includes steps/milestones
- **Acceptance criteria artifact** (`artifact.kind = ac.v1`)
  - explicit AC list with IDs (`AC-1`, `AC-2`, …)
- **Evidence plan artifact** (`artifact.kind = evidence-plan.v1`)
  - maps each AC to proposed evidence items

Validator checks:

- plan exists and is linked to `correlation_id`
- AC list exists and is non-empty
- evidence plan includes all AC IDs (see mapping rules)

### PLANNED → IN_PROGRESS (`work.started`)

Required:

- **Work reference** (`artifact.kind = work-ref.v1`)
  - branch name, commit, PR link, or change-set reference

Validator checks:

- work ref exists and includes immutable identifiers (commit SHA, PR number, etc.)

### IN_PROGRESS → REVIEWED (`review.recorded`)

Required:

- **Peer review record** (`artifact.kind = peer-review.v1`)
  - reviewer identity
  - timestamp
  - decision (`approved | changes_requested | rejected`)
  - notes

Validator checks:

- reviewer identity is present
- reviewer is not the implementer (SoD)

### REVIEWED → VALIDATED (`validation.completed`)

Required:

- **Validation bundle** (`artifact.kind = validation-bundle.v1`)
  - CI run IDs (or equivalent)
  - pass/fail summary
  - logs and test report links
- **Evidence bundle** (`artifact.kind = evidence-bundle.v1`)
  - links all evidence for the story (including review record)

Validator checks:

- required checks passed (`result = pass`)
- evidence bundle exists and references:
  - peer review artifact
  - CI logs/reports artifacts
- AC → evidence mapping is satisfied (see below)

### VALIDATED → VERIFIED (`vda.decision.recorded`)

Required:

- **VDA decision record** (`artifact.kind = vda-decision.v1`)
  - vda identity
  - timestamp
  - decision (`approve | deny | defer`)
  - rationale
  - explicit evidence bundle references

Validator checks (gate enforcement):

- decision is `approve`
- VDA is not implementer (SoD)
- peer review exists AND reviewer is not implementer (SoD)
- validation bundle exists and is green
- evidence mapping rules satisfied for all AC

---

## Evidence mapping rules (validator requirements)

Definitions:

- **AC catalog**: list of acceptance criteria IDs.
- **Evidence items**: artifacts of kinds like `test-report`, `qa-screenshot`, `ci-run-log`, `report`.

Rules:

- **GATE-EM-1**: every AC ID maps to ≥1 evidence item reference
- **GATE-EM-2**: all evidence references are immutable (hash or write-once ID)
- **GATE-EM-3**: all evidence items include `correlation_id` (traceability)

---

## Validator enforcement algorithm (reference)

The validator should enforce gates deterministically:

1) **Load intent state** and requested transition `(from, to, trigger)`.
2) **Verify transition is allowed** (table above). If not, reject.
3) **Load required artifacts** for the transition.
4) **Validate artifacts**:
   - existence
   - immutability
   - required fields present
   - actor identity constraints (SoD)
5) **Validate AC → evidence mapping** when entering VALIDATED and VERIFIED.
6) **Emit audit log events**:
   - `gate.pass` or `gate.fail` with reasons and evidence refs.

Recommended failure output (for auditability):

- error code (`missing_artifact`, `invalid_transition`, `sod_violation`, `mapping_incomplete`, `validation_failed`)
- human-readable explanation
- evidence refs consulted

