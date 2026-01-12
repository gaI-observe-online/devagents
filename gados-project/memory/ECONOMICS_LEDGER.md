# Economics Ledger (Usage + Cost)

**Status**: Authoritative / Evolves slowly  
**Purpose**: Define a simple, auditable, feature-level ledger for usage and cost signals that drive pricing and re-architecture triggers.

## Storage
Write append-only JSON Lines to:
- `/gados-project/log/economics/ledger.jsonl`

Each line is a single JSON object. Corrections are appended as new lines (never rewrite history).

## Schema (v1)
Each record MUST conform to:

- `schema`: `gados.economics.ledger.v1`
- `at`: ISO-8601 UTC timestamp
- `period`: `hourly` | `daily` | `weekly`
- `service`: string (e.g. `gados-control-plane`)
- `feature`:
  - `name`: string (e.g. `reports.daily_digest`)
  - `story_id` (optional): `STORY-###`
- `usage`:
  - `requests`: integer
  - `errors`: integer
  - `p50_ms` (optional): number
  - `p95_ms` (optional): number
- `ai_cost` (optional):
  - `provider`: string
  - `model`: string
  - `tokens_in`: integer
  - `tokens_out`: integer
  - `usd`: number
- `infra_cost` (optional):
  - `usd`: number
- `notes` (optional): string

## Thresholds (default triggers)
These are *defaults*; teams may tune them but must record changes in an ADR.

- **Margin floor trigger**: if `ai_cost.usd + infra_cost.usd` grows faster than expected for a feature, open an escalation.
- **Performance trigger**: if `p95_ms` exceeds threshold (e.g. 1500ms) for 3 consecutive periods, open an escalation.
- **Error trigger**: if `errors / requests` exceeds threshold (e.g. 2%) for 3 consecutive periods, open an escalation.

## Escalation payload templates
When a threshold is exceeded, Coordination Agent should create:
- `decision/ESCALATION-###.md` (human decision)
and also send a bus message:
- `type`: `ECONOMICS_THRESHOLD_BREACHED`
- `severity`: `WARN` (or `CRITICAL` if severe)
- `artifact_refs`: include the relevant ledger lines (or a pointer to a date range)
- `payload`:
  - `trigger`: `margin` | `performance` | `error`
  - `feature.name`
  - `observed`: object (actual metrics/cost)
  - `threshold`: object
  - `recommended_action`: string

