# Verification Policy (VDA)

**Status**: Authoritative / Evolves slowly  
**Purpose**: Define what “VERIFIED” means, what evidence is required, and how certification is audited.

## Definition of VERIFIED
A story is `VERIFIED` only when all acceptance criteria are satisfied **with evidence**, and the verification decision is made by the **Delivery Governor (VDA)** (independent from the implementer).

## Required artifacts for VERIFIED
For `STORY-###`:

- Story spec: `plan/stories/STORY-###.md`
- Approved change plan: `plan/changes/CHANGE-###-<suffix>.yaml` (VDA-approved)
- QA evidence package: `verification/STORY-###-evidence.md`
- Peer review report: `verification/STORY-###-review.md`
- Append-only audit log: `log/STORY-###.log.yaml` containing a `VERIFICATION_DECISION` event

## Evidence mapping rules
Evidence must map to acceptance criteria explicitly:
- Each acceptance criterion must have at least one evidence item.
- Evidence should be reproducible: command outputs, logs, screenshots, metrics as applicable.
- Evidence must include environment details (versions/config where relevant).

## Independence rules (separation of duties)
- Implementer (Execution Engine / Vibe) cannot author the VDA decision.
- QA evidence and peer review must be authored by distinct roles/agents.
- If independence cannot be achieved, the story must be **ESCALATED** for Human Authority decision.

## VDA decision outcomes
The VDA must write one of:
- `VERIFIED`
- `REJECTED` (with required fix notes and evidence gaps)
- `ESCALATED` (with brief + risk classification)

Decision and rationale must be recorded in `log/STORY-###.log.yaml`.

## Minimum log events (audit trail)
The story log should contain (at minimum):
- `STATUS_CHANGED` to `IN_PROGRESS`
- `EVIDENCE_ATTACHED` referencing the evidence package
- `PEER_REVIEW_ATTACHED` referencing the peer review
- `VERIFICATION_DECISION` referencing both artifacts and the decision rationale

