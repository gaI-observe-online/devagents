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

