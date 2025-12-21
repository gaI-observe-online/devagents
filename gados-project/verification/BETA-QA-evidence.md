# BETA QA Evidence Package

**Prepared by (QA Agent)**: <name>  
**Date (UTC)**: <YYYY-MM-DD>  
**Environment**: <local/VPN host, OS, Python, Docker versions>

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
<paste>
```

### 2) Unit tests (pytest)
Command:

```bash
python3 -m pytest -q
```

Output:

```
<paste>
```

### 3) Governance validator
Command:

```bash
python3 gados-control-plane/scripts/validate_artifacts.py
```

Output:

```
<paste>
```

### 4) Notification digest flush tooling
Commands:

```bash
make notify-digest-flush
```

Evidence:
- Confirm a file was written under `gados-project/log/reports/NOTIFICATIONS-YYYYMMDD.md` (attach path + snippet).

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
- **PASS** / **FAIL**:
- Issues discovered:
  - ...

