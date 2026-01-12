# Agent bus (audit log)

This folder contains append-only logs for **agent-to-agent communication**.

- `bus-events.jsonl`: append-only JSON lines log of `MESSAGE_SENT`, `ACKED`, `NACKED`, `DEAD_LETTERED`.

Runtime queue state (SQLite) is stored outside git under `.gados-runtime/`.

