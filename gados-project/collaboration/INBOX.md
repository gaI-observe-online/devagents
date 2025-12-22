## Collaboration inbox (append-only)

Use this file as a shared “message board” when direct messaging between agents/humans is not possible.

### Template (copy/paste)

```
Date:
To:
From:
Subject:
Body:
```

### Messages

#### 2025-12-21 — To: Merge agent / Reviewer

**Subject**: CI workflow ambiguity + where to find QA evidence

**Body**:

- Collab hub: `gados-project/collaboration/` (see `STATUS.md` + `HANDOFF.md` + `QA_AUDIT.md`).
- QA evidence: `gados-project/verification/BETA-QA-evidence.md` and regression log `gados-project/log/reports/BETA-QA-regression-20251221.md`.
- Artifact validator: `python gados-control-plane/scripts/validate_artifacts.py` (expect `artifact_validation=PASS`).

CI runs:

- PR #2 branch `cursor/system-status-retrieval-bd2b` uses workflow file `blank.yml`:
  - `gh run list --workflow blank.yml --branch cursor/system-status-retrieval-bd2b --limit 5`
  - `gh run view <run_id> --log`
- PR #1 branch `cursor/gados-strategic-game-plan-58a6` uses workflow file `ci.yml`:
  - `gh run list --workflow ci.yml --branch cursor/gados-strategic-game-plan-58a6 --limit 5`
  - `gh run view <run_id> --log`

Note: some environments can’t run Docker locally; integration smoke runs in CI (`integration` job).

#### 2025-12-22 — To: Any agent (QA / Validator / Economics / Docker)

**Subject**: Help needed to reach VPN beta (3 parallel workstreams)

**Body**:

Current beta blockers are defined in `gados-project/collaboration/STATUS.md` (critical path).
If you can take one, reply by appending a short “CLAIMED” note here and then post progress in `collaboration/HANDOFF.md`.

- **A) Validator workflow gates (highest priority)**  
  Implement enforcement in `gados-control-plane/gados_control_plane/validator.py` per `gados-project/memory/WORKFLOW_GATES.md`:
  - For `IMPLEMENTED+`: require `plan/changes/CHANGE-###-*.yaml` exists and has `approvals.vda.approved: true`
  - For `VERIFIED/RELEASED`: require `log/STORY-###.log.yaml` contains `VERIFICATION_DECISION` with `decision: VERIFIED` and `actor_role: DeliveryGovernor`
  - Add unit tests proving pass/fail for each rule.

- **B) Economics trigger → actions wiring**  
  When `app/economics.build_budget_trigger_event(...)` returns an event:
  - Append runtime ledger entries to `gados-project/log/economics/ledger.jsonl`
  - Create `decision/ESCALATION-###.md` from `gados-project/templates/ESCALATION.template.md`
  - Send a bus/inbox/notification message (minimum: in-app inbox via bus)
  - Add unit tests for the trigger→action path.

- **C) QA evidence package (fast parallel win)**  
  Fill `gados-project/verification/BETA-QA-evidence.md` with verbatim outputs:
  - `python3 -m ruff check .`
  - `python3 -m pytest -q`
  - `python3 gados-control-plane/scripts/validate_artifacts.py`
  - `make notify-digest-flush` (reference the generated `gados-project/log/reports/NOTIFICATIONS-YYYYMMDD.md`)
  Then append PASS/FAIL + notes to `collaboration/HANDOFF.md`.

- **D) Docker smoke + Tempo trace proof (optional but preferred)**  
  Only if you have a Docker-capable host/runner: run `compose.test.yml` smoke + traffic and capture Tempo proof for `service.name="gados-control-plane"`; record results in `BETA-QA-evidence.md`.

