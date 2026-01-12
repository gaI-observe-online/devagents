# Workflow Gates (State Machine + Enforcement)

**Status**: Authoritative / Evolves slowly  
**Purpose**: Define the exact story lifecycle and the minimum artifacts required to advance states.

## Canonical states
`PLANNED → IN_PROGRESS → IMPLEMENTED → QA_EVIDENCE_READY → PEER_REVIEWED → VERIFIED → RELEASED → ESCALATED`

Only **VDA** can advance to `VERIFIED`.

## Required artifacts by transition

### PLANNED → IN_PROGRESS
**Required**
- `plan/stories/STORY-###.md`
- `log/STORY-###.log.yaml` with a `STATUS_CHANGED` event to `IN_PROGRESS`
**Actor**
- Coordination Agent

### IN_PROGRESS → IMPLEMENTED
**Required**
- Approved change plan: `plan/changes/CHANGE-###-*.yaml` with `approvals.vda.approved: true`
**Actor**
- Execution Engine (Vibe) implements code; CA records status update

### IMPLEMENTED → QA_EVIDENCE_READY
**Required**
- `verification/STORY-###-evidence.md`
- `log/STORY-###.log.yaml` contains `EVIDENCE_ATTACHED` referencing the evidence artifact
**Actor**
- QA Agent

### QA_EVIDENCE_READY → PEER_REVIEWED
**Required**
- `verification/STORY-###-review.md`
- `log/STORY-###.log.yaml` contains `PEER_REVIEW_ATTACHED` referencing the review artifact
**Actor**
- Peer Reviewer

### PEER_REVIEWED → VERIFIED
**Required**
- `verification/STORY-###-evidence.md` exists
- `verification/STORY-###-review.md` exists
- `log/STORY-###.log.yaml` contains `VERIFICATION_DECISION` with:
  - `decision: VERIFIED`
  - references to evidence + review artifacts
  - `actor_role: DeliveryGovernor`
**Independence**
- Implementer identity must differ from verifier identity (store identities in log events or story metadata)
**Actor**
- Delivery Governor (VDA)

### VERIFIED → RELEASED
**Required**
- Release signal (project-specific). For MVP, allow CA to record status change with a reference to deployment evidence.
**Actor**
- Coordination Agent

### Any → ESCALATED
**Required**
- `decision/ESCALATION-###.md` (Human Authority decision record)
- Story log references escalation artifact
**Actor**
- Coordination Agent routes; Human Authority decides

## Validator enforcement algorithm (MVP)
For each `STORY-###.md`:
1. Parse `**Status**:` line.
2. If status includes `VERIFIED` or `RELEASED`:
   - Require evidence + peer review artifacts exist.
   - Require story log exists.
   - Parse story log and require a `VERIFICATION_DECISION` with `decision: VERIFIED`.
3. If story declares `IMPLEMENTED` or beyond:
   - Require at least one change plan exists for the story and is VDA-approved.

## Notes
These gates are intentionally minimal. Tightening (auth/RBAC, strict identity checks, ADR enforcement for re-architecture) should be recorded as ADRs and iterated without losing auditability.

