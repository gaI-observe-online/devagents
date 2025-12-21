## BETA QA regression run — 2025-12-21

Commit under test: `066e9e1350ad1083a331ef7e94897a6d19c5b815`

### Summary

- **Passed**: ruff, pytest
- **Now passing**: artifacts validator script exists and runs (`gados-control-plane/scripts/validate_artifacts.py`)
- **Blocked**: Docker-based integration checks (Docker not installed in this environment)

### Commands executed + results

- `python3 -m ruff check .` → PASS
- `python3 -m pytest -q` → PASS
- `python3 gados-control-plane/scripts/validate_artifacts.py` → PASS

### Flakes

- None observed in this environment.

### Follow-up issues

- **Integration targets**: `make test-env-up/test-smoke/test-env-down` now exist, but still require Docker.
- **Service health endpoint**: `make test-smoke` assumes a service is running at `http://localhost:8000/health` (ensure control-plane is started in Docker-capable regression environment).
- **Grafana health**: `make test-smoke` assumes Grafana is running at `http://localhost:3000/api/health` (requires Docker compose up).

