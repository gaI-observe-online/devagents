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

#### 2025-12-22 — To: Merge agent / New QA agent

**Subject**: QA evidence completed (static/unit/validator/notifications) + new reports

**Body**:

QA evidence has been updated with fresh verbatim outputs and new reports were added:

- Updated: `gados-project/verification/BETA-QA-evidence.md` (includes notifications digest flush evidence)
- Added: `gados-project/log/reports/BETA-QA-regression-20251222.md`
- Added: `gados-project/log/reports/NOTIFICATIONS-20251222.md`

Docker/integration remains BLOCKED on this runner (no Docker). CI `integration` job is the recommended source of Docker smoke evidence.

#### 2025-12-22 — To: Any agent (tracebacks)

**Subject**: Traceback captured + resolution

**Body**:

We captured and documented a real traceback that occurred during regression evidence collection:

- `scripts/flush_digest.py` initially failed with `ModuleNotFoundError: No module named 'app'`
- Fix: update `scripts/flush_digest.py` to add repo root to `sys.path` before importing `app.*`
- Traceback + note recorded in `gados-project/collaboration/QA_AUDIT.md`

#### 2025-12-23 — To: Merge agent / Anyone unblocking PR #3

**Subject**: PR #3 unblock checklist — failing `docker_smoke` + `review_pack` + Windows Docker test steps

**Body**:

Two remaining failing checks on PR #3 (`cursor/gados-game-plan-agent-replacement-3913`):

- `CI / docker_smoke`: LGTM container `otel-lgtm-test` is marked unhealthy because `compose.test.yml` uses `wget` inside `grafana/otel-lgtm:0.9.2` for healthcheck.
  - Fix: change LGTM healthcheck to the readiness file the image creates:
    - `healthcheck.test: ["CMD-SHELL", "test -f /tmp/ready"]`
    - bump `retries` to `60` (optional but reduces flake).
- `Code Review Factory (Audit Pack) / review_pack`: NO-GO due to `Secrets detected (1)` from `detect-secrets`.
  - Root cause: `gados-project/verification/PM-WALKTHROUGH.md` includes the literal marker `-----BEGIN PRIVATE KEY-----`.
  - Fix: remove the literal PEM marker from the repo; use a runtime-generated key snippet instead (e.g., `ssh-keygen ...; cp ...; rm ...`), keeping cleanup of the seeded file.

Minimal local verification (after rebase completes):

- `python -m ruff check .`
- `python -m pytest -q -m "not integration"`
- `python gados-control-plane/scripts/validate_artifacts.py`
- `python scripts/generate_review_pack.py` (should exit 0 once the secret marker is removed)

Windows Docker smoke (Docker Desktop + WSL2):

- `docker compose -f compose.test.yml up -d --build`
- `curl http://localhost:3000/api/health`
- `curl http://localhost:8000/health`
- `docker compose -f compose.test.yml down -v`

