## BETA QA regression run — 2025-12-22

Commit under test: `ffdbf8d0d39a0620d10a5734680cb5e70fa64e78`

### Summary

- **Passed**: ruff, pytest, artifact validator, notifications digest flush (local receiver)
- **Blocked locally**: Docker integration (Docker not installed on this runner)
- **Next**: run integration evidence on Docker-capable host or rely on CI `integration` job logs

### Commands executed + results (verbatim)

```bash
python3 -m ruff check .
All checks passed!
```

```bash
python3 -m pytest -q
.................                                                        [100%]
17 passed in 0.51s
```

```bash
python3 gados-control-plane/scripts/validate_artifacts.py
artifact_validation=PASS
```

```bash
# Notification digest flush evidence recorded in:
# - gados-project/log/reports/NOTIFICATIONS-20251222.md
```

### Flakes

- None observed.

### Follow-up issues / blockers

- Docker unavailable locally; integration smoke and Tempo trace proof must run in CI or Docker-capable environment.

