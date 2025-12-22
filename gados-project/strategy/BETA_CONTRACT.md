# Beta Contract (release definition)

This document defines what “beta” means for this repository: supported environments, required configuration, and the success gates.

## Supported environments
- **OS**: Linux (primary). macOS is expected to work for local runs.
- **Python**: **3.11+** (CI uses 3.11; local runs validated on 3.12).
- **Docker**: **not required** for beta (optional for LGTM stack + docker smoke profile).

## Required configuration
- **None required** for a local run.
- Optional (documented in `.env.example`):
  - `GADOS_BASIC_AUTH_USER` / `GADOS_BASIC_AUTH_PASSWORD` (enables auth for write endpoints)
  - `GADOS_RUNTIME_DIR` (runtime state location)
  - OTel export vars (optional; `OTEL_SDK_DISABLED=1` default)

## Golden path (10 minutes)
```bash
cp .env.example .env
make beta-up
make beta-verify
```

## Beta acceptance gates (PASS/FAIL)
- `python -m ruff check .` **PASS**
- `python -m pytest -q` **PASS**
- `python gados-control-plane/scripts/validate_artifacts.py` **PASS**
- `make notify-digest-flush` produces `gados-project/log/reports/NOTIFICATIONS-YYYYMMDD.md`

## Optional (nice-to-have)
- Docker smoke + Tempo proof on Docker-capable host.

