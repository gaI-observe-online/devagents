## Shared status board

Last updated: 2025-12-22 (QA evidence completed)

### Active PRs / branches

| Workstream | Owner | Branch / PR | Status | Next step | Blockers |
|---|---|---|---|---|---|
| Analytics + Observability starter kit | Agent | `cursor/system-status-retrieval-bd2b` / PR #2 | READY_TO_MERGE | Merge PR #2 after CI green | Docker integration is CI-only |
| GADOS strategic plan | Agent | `cursor/gados-strategic-game-plan-58a6` / PR #1 | IN_PROGRESS | Review + reconcile docs | None |
| New agent replacement (validator/economics wiring) | Agent | `cursor/gados-game-plan-agent-replacement-3913` | IN_PROGRESS | Implement workflow-gate enforcement + economics trigger wiring | See `HANDOFF.md` 2025-12-22 guidance |

### QA status (beta)

- **Evidence artifact**: `gados-project/verification/BETA-QA-evidence.md`
- **Template**: `gados-project/verification/BETA-QA-evidence-TEMPLATE.md`
- **Regression plan**: `gados-project/verification/BETA-REGRESSION-PLAN.md`
- **Evidence pack checklist**: `gados-project/verification/BETA-EVIDENCE-PACK-CHECKLIST.md`
- **Regression log**: `gados-project/log/reports/BETA-QA-regression-20251221.md`
- **Regression log (latest)**: `gados-project/log/reports/BETA-QA-regression-20251222.md`
- **Notifications report (latest)**: `gados-project/log/reports/NOTIFICATIONS-20251222.md`
- **QA audit evidence**: `gados-project/collaboration/QA_AUDIT.md` (PASS + controlled FAIL examples)
- **Collab inbox**: `gados-project/collaboration/INBOX.md` (async messages for other agents)
- **Integration code review notes**: `gados-project/collaboration/HANDOFF.md` (2025-12-21 entry)
- **Latest results**:
  - **PASS**: `python3 -m ruff check .`, `python3 -m pytest -q`
  - **PASS**: `python3 gados-control-plane/scripts/validate_artifacts.py` (`artifact_validation=PASS`)
  - **PASS**: notifications digest flush (see `NOTIFICATIONS-20251222.md`)
  - **PARTIAL (local alt)**: no-Docker smoke covers `/health` + `/track` and compose port sanity (see `tests/test_integration_nodocker_smoke.py`)
  - **BLOCKED (local docker)**: Docker integration steps (Docker not installed in this environment)
  - **MOVED (CI)**: Docker/integration smoke now runs in GitHub Actions `integration` job

### QA decision (beta)

- **GO (from QA)**: Yes — based on passing static/unit/validator/notifications checks and the no-Docker smoke alternative, with Docker integration evidence sourced from CI.
- **Remaining**: optional Docker/Tempo proof capture on a Docker-capable host (if required for audit pack completeness).

### Progress update (2025-12-22)

- Added regression planning artifacts (pipeline stages + policy gates + evidence pack checklist).
- Updated QA evidence template to include pipeline/policy/offline ACs and references.
- Pending merge on this branch: new/updated files under `gados-project/verification/` and updated collab docs (see `HANDOFF.md` 2025-12-22 entry).

### Known blockers / gaps

- **Integration requires Docker-capable runner** for `make test-env-up/test-smoke/test-env-down` and Grafana/Tempo checks.
- **Pending merge (critical path hardening)**: see `gados-project/collaboration/HANDOFF.md` (2025-12-21 entry); files: `.github/workflows/blank.yml`, `Makefile`, `app/main.py`
- **Workflow name ambiguity**: there are two workflows named `CI` (`blank.yml` and `ci.yml`); use `--workflow blank.yml` or `--workflow ci.yml` when querying runs.

