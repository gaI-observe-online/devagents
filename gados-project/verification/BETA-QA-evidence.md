# BETA QA Evidence Package

**Prepared by (QA Agent)**: Coordination Agent (automation evidence)  
**Date (UTC)**: 2025-12-22  
**Environment**: Linux (CI-like), Python 3.12, Docker: not required for beta

## Scope
Validate VPN beta readiness for:
- Control plane UI + governance validator
- Agent bus
- Notifications (queue + digest flush; webhook optional)
- Economics (ledger writer functions + trigger payloads)
- Docker smoke (LGTM + control-plane) if Docker available

## Evidence checklist (commands + outputs)

### 1) Static checks (ruff)
Command:

```bash
python3 -m ruff check .
```

Output:

```
All checks passed!
```

### 2) Unit tests (pytest)
Command:

```bash
python3 -m pytest -q
```

Output:

```
....sss.............                                                     [100%]
17 passed, 3 skipped in 0.37s
```

### 3) Governance validator
Command:

```bash
python3 gados-control-plane/scripts/validate_artifacts.py
```

Output:

```
INFO: OK - All validations passed.
```

### 4) Notification digest flush tooling
Commands:

```bash
make notify-digest-flush
```

Evidence:
- Wrote: `gados-project/log/reports/NOTIFICATIONS-20251222.md`
- Snippet:
  - `(no queued notifications)`

### 5) Docker smoke (optional but preferred)
If Docker is available:

```bash
make test-env-up
curl -fsS http://localhost:3000/api/health
curl -fsS http://localhost:8000/health
make test-smoke
make test
make test-env-down
```

Evidence:
- `curl` outputs
- If possible: a screenshot or short note from Grafana Explore → Tempo confirming traces for `service.name="gados-control-plane"`.

## Findings
- **PASS**:
- Issues discovered:
  - Docker/Tempo proof: NOT REQUIRED for beta (per product decision)

