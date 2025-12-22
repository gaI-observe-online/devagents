# STATUS (Shared)

Last updated (UTC): 2025-12-22

## Workstreams
- **Governance enforcement**: workflow gates now enforced in validator (IMPLEMENTED+ requires VDA-approved change plan; VERIFIED/RELEASED requires VERIFICATION_DECISION by DeliveryGovernor) + unit tests added
- **Control plane UI**: dashboard/artifacts/create/reports/inbox/decisions live (FastAPI + templates)
- **Agent bus + notifications**: bus live; notifications module + digest flush tooling integrated; webhook integration not yet wired into control-plane UI
- **Economics loop**: guardrail scenario wired end-to-end (ledger JSONL + threshold trigger → escalation decision artifact + bus + notification) and tested
- **Observability tightening**: awaiting handoff entry (branch/PR + verification evidence) in `collaboration/HANDOFF.md`
- **QA / evidence**: beta evidence package filled at `gados-project/verification/BETA-QA-evidence.md` and handoff updated

## Critical path (VPN beta)
1. **Enforce workflow gates in code** (implement `WORKFLOW_GATES.md` in validator: parse story logs for `VERIFICATION_DECISION`, require VDA-approved change plan for `IMPLEMENTED+`, enforce VDA-only VERIFIED).
2. **Wire economics triggers to actions** (append to `log/economics/ledger.jsonl` in runtime + on threshold breach create escalation artifact + send notification/bus message).
3. **Complete QA evidence** (fill `verification/BETA-QA-evidence.md`; Docker/Tempo proof optional but preferred).

## Definition of Done (critical path)

### 1) Workflow gates enforced (code)
- **Validator behavior**:
  - If a story is `VERIFIED`/`RELEASED`: validator **must** parse `log/STORY-###.log.yaml` and require a `VERIFICATION_DECISION` with `decision: VERIFIED` and `actor_role: DeliveryGovernor`.
  - If a story is `IMPLEMENTED` or beyond: validator **must** require a `CHANGE-###-*.yaml` exists and has `approvals.vda.approved: true`.
- **Tests**: unit tests prove validator fails/passes for each rule.
- **CI**: unit job runs validator and fails on violations.

### 2) Economics triggers wired to actions
- **Ledger**: a runtime job/app hook writes valid JSONL lines to `gados-project/log/economics/ledger.jsonl` (append-only).
- **Trigger action**: when `build_budget_trigger_event(...)` returns a threshold event:
  - Create `decision/ESCALATION-###.md` (or ADR if it’s a re-architecture trigger) **and**
  - Send a bus/notification event (at least to in-app inbox; webhook optional).
- **Tests**: unit tests for ledger append + trigger→action wiring.

### 3) QA evidence complete
- `gados-project/verification/BETA-QA-evidence.md` filled with:
  - verbatim outputs for ruff/pytest/validator
  - digest flush evidence (`NOTIFICATIONS-YYYYMMDD.md`)
  - Docker/Tempo proof if available (optional but preferred)
- QA appends PASS/FAIL outcome to `collaboration/HANDOFF.md`.

## Blockers
- Docker-based LGTM validation requires a machine with Docker. Mitigation: integration tests are now optional by default; CI runs docker smoke as a non-blocking job.

## QA snapshot
- **ruff**: PASS (`python3 -m ruff check .`)
- **pytest**: PASS (`python3 -m pytest -q -m "not integration"`)
- **governance validator**: PASS (`python3 gados-control-plane/scripts/validate_artifacts.py`)
- **docker smoke (LGTM + control-plane)**: OPTIONAL (run via `make test-env-up && make test-smoke && make test-integration && make test-env-down` on Docker-capable host)

