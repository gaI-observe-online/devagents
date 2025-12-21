# STATUS (Shared)

Last updated (UTC): 2025-12-21

## Workstreams
- **Governance enforcement**: policies + validator + CI checks in place; enforcement tightening (WORKFLOW_GATES parsing) pending
- **Control plane UI**: dashboard/artifacts/create/reports/inbox/decisions live (FastAPI + templates)
- **Agent bus + notifications**: bus live; notifications module + digest flush tooling integrated; webhook integration not yet wired into control-plane UI
- **Economics loop**: economics ledger spec + economics module + tests present; runtime ledger writer + trigger-to-escalation wiring pending
- **QA / evidence**: QA agent assigned; evidence package to be produced at `gados-project/verification/BETA-QA-evidence.md`

## Blockers
- Docker-based LGTM validation requires a machine with Docker. Mitigation: integration tests are now optional by default; CI runs docker smoke as a non-blocking job.

## QA snapshot
- **ruff**: PASS (`python3 -m ruff check .`)
- **pytest**: PASS (`python3 -m pytest -q -m "not integration"`)
- **governance validator**: PASS (`python3 gados-control-plane/scripts/validate_artifacts.py`)
- **docker smoke (LGTM + control-plane)**: OPTIONAL (run via `make test-env-up && make test-smoke && make test-integration && make test-env-down` on Docker-capable host)

