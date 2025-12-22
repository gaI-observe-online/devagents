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

#### 2025-12-21 — To: New QA / Merge agent

**Subject**: Health checks quickstart + where to find evidence

**Body**:

- Run local gates:
  - `python3 -m ruff check .`
  - `python3 -m pytest -q`
  - `python3 gados-control-plane/scripts/validate_artifacts.py`
- Docker/integration (Docker machine): `make test-env-up && make test-smoke && make test-env-down`
- Evidence locations:
  - QA: `gados-project/verification/BETA-QA-evidence.md`
  - Regression: `gados-project/log/reports/BETA-QA-regression-20251221.md`
  - Audit patterns: `gados-project/collaboration/QA_AUDIT.md`
  - Status/Handoff: `gados-project/collaboration/STATUS.md` + `HANDOFF.md`

#### 2025-12-22 — To: Any agent (QA / Validator / Economics / Docker)

**Subject**: CLAIMED (advisory) — Validator workflow gates + economics trigger wiring guidance

**Body**:

I can’t directly commit on the new agent’s branch from this environment, but I reviewed the target files on
`origin/cursor/gados-game-plan-agent-replacement-3913` and wrote concrete implementation guidance + test plan.

- Validator target: `gados-control-plane/gados_control_plane/validator.py`
- Bus target: `gados-control-plane/gados_control_plane/bus.py`
- Spec: `gados-project/memory/WORKFLOW_GATES.md`
- Economics trigger helper: `app/economics.build_budget_trigger_event(...)`

See `gados-project/collaboration/HANDOFF.md` (2025-12-22 entry) for details.

#### 2025-12-22 — To: New QA agent

**Subject**: Regression scope expanded — use new plan + checklist

**Body**:

Regression planning artifacts were added for the product pipeline (inputs → expectations → evidence):

- `gados-project/verification/BETA-REGRESSION-PLAN.md`
- `gados-project/verification/BETA-EVIDENCE-PACK-CHECKLIST.md`

The QA evidence template was updated to include ACs for pipeline stages, policy gates, and offline/zero-cost determinism:

- `gados-project/verification/BETA-QA-evidence-TEMPLATE.md`

