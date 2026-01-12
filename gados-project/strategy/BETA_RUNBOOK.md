# Beta Runbook (Local-first)

This page is the **single “beta operator” guide**: how to start, verify, inspect logs, reset state, and capture QA evidence.

## Start (golden path)

```bash
cp .env.example .env
make beta-up
```

Open: `http://127.0.0.1:8000`

## Verify it’s working

```bash
make beta-verify
```

Manual checks:
- Health: `http://127.0.0.1:8000/health`
- UI: `http://127.0.0.1:8000/`
- Validator UI: `http://127.0.0.1:8000/validate`
- Inbox UI: `http://127.0.0.1:8000/inbox`
- Reports UI: `http://127.0.0.1:8000/reports`

## Where data/logs live

### Runtime (ephemeral/local)
- Control-plane process log: `.gados-runtime/control-plane.log`
- Control-plane PID file: `.gados-runtime/control-plane.pid`
- Agent bus runtime DB (durable queue): `.gados-runtime/bus.sqlite3` (or `$GADOS_RUNTIME_DIR/bus.sqlite3`)
- Notification queue (JSONL): `.gados-runtime/notifications.queue.jsonl`

### Versioned audit artifacts (in repo)
- Bus append-only audit log: `gados-project/log/bus/bus-events.jsonl`
- Reports: `gados-project/log/reports/`
- Decision records: `gados-project/decision/`
- Governance + policies: `gados-project/memory/`

## Stop / reset

Stop:

```bash
make beta-down
```

Reset local runtime state:

```bash
make beta-reset
```

## Observability (optional)

If you have Docker:

```bash
make obs-up
```

- Grafana: `http://localhost:3000`
- OTLP HTTP endpoint: `http://localhost:4318`

Tear down:

```bash
make obs-down
```

## Grafana Cloud (free) clickpath (optional)

See: `gados-project/strategy/GRAFANA_CLOUD_CLICKPATH.md`

## Capture QA evidence (beta proof)

Fill: `gados-project/verification/BETA-QA-evidence.md`

Commands:

```bash
python3 -m ruff check .
python3 -m pytest -q
python3 gados-control-plane/scripts/validate_artifacts.py
make notify-digest-flush
```

Evidence:
- Attach verbatim outputs for the commands above.
- Reference the generated digest: `gados-project/log/reports/NOTIFICATIONS-YYYYMMDD.md`.
- If Docker is available, optionally run `make test-docker` and include the results.

