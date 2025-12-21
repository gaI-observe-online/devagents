# ARCH RULES (Authoritative Memory)

**Status**: Authoritative / Evolves slowly  
**Purpose**: Technical guardrails that prevent architectural drift and governance bypass.

## 1) Artifact directory structure (must remain stable)
All delivery artifacts live under `/gados-project/` with these top-level domains:

- `memory/` authoritative memory (foundation + principles + rules)
- `strategy/` strategic plans (epics)
- `plan/` story specs + approved change plans
- `log/` append-only delivery audit logs
- `decision/` escalation decisions (human authority)
- `verification/` evidence packages and peer reviews

## 2) Story and change plan naming
- Stories: `STORY-###.md` (e.g., `STORY-014.md`)
- Change plans: `CHANGE-###-<suffix>.yaml` (e.g., `CHANGE-014-A.yaml`)
- Logs: `STORY-###.log.yaml`
- Evidence: `STORY-###-evidence.md`
- Peer review: `STORY-###-review.md`
- Escalations: `ESCALATION-###.md`
- Epics: `EPIC-###.md` and optional metadata `EPIC-###.yaml`

## 3) Append-only audit logs
Logs in `/gados-project/log/` must be treated as **append-only**.
If a correction is required, append a correcting event; do not rewrite history.

## 4) Verification gatekeeping
- Only VDA can mark a story as `VERIFIED`.
- Verification requires evidence that maps to acceptance criteria.
- Evidence packages must include command outputs, screenshots/logs where relevant, and test results.

## 5) Change authorization rules
Execution work must be bounded by an **approved change plan** artifact that includes:
- scope / files touched (allowlist)
- acceptance criteria reference
- test plan
- rollback plan

## 6) Separation-of-duties enforcement (process constraint)
- The implementer cannot author the verification decision.
- Peer review and QA evidence must be independent inputs.

## 7) Economics and re-architecture triggers
Any pricing decision or re-architecture trigger must cite:
- usage/cost data
- margin impact
- rationale and alternatives
and must be logged as a decision artifact when it changes direction.

