## BETA QA evidence package

Date: 2025-12-21  
Repo: `gaI-observe-online/devagents`  
Commit under test: `066e9e1350ad1083a331ef7e94897a6d19c5b815`

### Environment

OS / Kernel:

```bash
uname -a
Linux cursor 6.1.147 #1 SMP PREEMPT_DYNAMIC Tue Aug  5 21:01:56 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux
```

Python / tooling:

```bash
python3 --version
Python 3.12.3

python3 -m pip --version
pip 24.0 from /usr/lib/python3/dist-packages/pip (python 3.12)

python3 -m ruff --version
ruff 0.8.4

python3 -m pytest --version
pytest 8.3.4
```

Docker:

```bash
docker --version
--: line 1: docker: command not found
```

---

## Acceptance criteria (beta)

These ACs map to the minimum workflows requested:

- **AC-CP-1 (control-plane smoke)**: basic unit/static checks pass.
- **AC-BUS-1 (bus)**: bus behavior is covered by unit tests for notification/digest queuing semantics (no runtime bus in this repo yet).
- **AC-NOTIF-1 (notifications)**: critical-only realtime + daily digest behavior is implemented and unit-tested.
- **AC-ECO-1 (economics)**: ledger writer and threshold trigger logic are implemented and unit-tested.
- **AC-VAL-1 (validator gate)**: artifact validation command exists and runs successfully.
- **AC-INT-1 (docker/integration)**: test env up, smoke, Grafana health, service health, Tempo trace verification, full test, env down.

---

## Commands run (verbatim) + outputs (verbatim)

### Static + unit

```bash
python3 -m ruff check .
All checks passed!
```

```bash
python3 -m pytest -q
.................                                                        [100%]
17 passed in 0.43s
```

```bash
python3 gados-control-plane/scripts/validate_artifacts.py
artifact_validation=PASS
```

### CI evidence (GitHub Actions)

Most recent successful workflow runs observed:

- PR #2 / `cursor/system-status-retrieval-bd2b` (`blank.yml`):
  - `gh run list --workflow blank.yml --branch cursor/system-status-retrieval-bd2b --limit 1`
  - Example run ID: `20407067806` (completed success)
- PR #1 / `cursor/gados-strategic-game-plan-58a6` (`ci.yml`):
  - `gh run list --workflow ci.yml --branch cursor/gados-strategic-game-plan-58a6 --limit 1`
  - Example run ID: `20407091818` (completed success)

### Docker / integration (attempted in this environment)

```bash
make test-env-up
BLOCKED: docker not installed
make: *** [Makefile:13: test-env-up] Error 2
```

```bash
curl -fsS http://localhost:3000/api/health
curl: (7) Failed to connect to localhost port 3000 after 0 ms: Couldn't connect to server
```

```bash
curl -fsS http://localhost:8000/health
curl: (7) Failed to connect to localhost port 8000 after 0 ms: Couldn't connect to server
```

```bash
make test-smoke
Smoke checks:
  - Grafana: http://localhost:3000/api/health
  - Service: http://localhost:8000/health
curl: (7) Failed to connect to localhost port 3000 after 0 ms: Couldn't connect to server
make: *** [Makefile:20: test-smoke] Error 7
```

```bash
make test
python3 -m pytest -q
.................                                                        [100%]
17 passed in 0.42s
```

```bash
make test-env-down
BLOCKED: docker not installed
make: *** [Makefile:24: test-env-down] Error 2
```

---

## Evidence mapped to acceptance criteria

| AC | Result | Evidence |
|---|---|---|
| AC-CP-1 | PASS | `python3 -m ruff check .` output; `python3 -m pytest -q` output |
| AC-BUS-1 | PASS (unit-only) | Notification digest enqueue/flush tests executed as part of pytest run (17 passing total) |
| AC-NOTIF-1 | PASS | `tests/test_notifications.py` executed in pytest run (part of 17 passing) |
| AC-ECO-1 | PASS | `tests/test_economics.py` executed in pytest run (part of 17 passing) |
| AC-VAL-1 | PASS | `python3 gados-control-plane/scripts/validate_artifacts.py` output (`artifact_validation=PASS`) |
| AC-INT-1 | BLOCKED | Docker not installed; Grafana/service endpoints not reachable in this environment |

---

## Notes / blockers

- **BLOCKER**: Docker is not available in this environment (`docker: command not found`), so Grafana/LGTM validation and any Docker-based integration run cannot be executed here.
- **NOTE**: `make test-env-up/test-smoke/test-env-down` now exist, but require Docker and a running stack.

