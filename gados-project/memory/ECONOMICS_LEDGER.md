## Economics loop: usage/cost ledger + thresholds (authoritative artifact)

This document defines the **Economics loop** for GADOS: how usage/cost is recorded as artifacts and how margin/trigger rules drive notifications/escalations.

### Goals

- Produce **audit-ready, versioned** cost artifacts for each run/intent.
- Provide deterministic **threshold rules** to trigger escalation.
- Keep the format stable to avoid rework across tooling (CI, validator, dashboard).

---

## Ledger artifact format

### Storage format

- **File type**: JSON Lines (one JSON object per line)
- **Recommended extension**: `.jsonl`
- **Artifact kind**: `economics.ledger.v1`

### Record schema (`economics.ledger.entry.v1`)

Required fields:

- **`schema`**: `"economics.ledger.entry.v1"`
- **`entry_id`**: globally unique (UUID)
- **`timestamp`**: ISO-8601 UTC
- **`correlation_id`**: ties to intent/run (e.g. `intent_id`)
- **`run_id`**: execution/run identifier (CI run ID, agent run ID)
- **`producer`**: `control-plane | agent | ci | validator`
- **`category`**: `llm | compute | storage | saas | human | other`
- **`unit`**: `tokens | seconds | bytes | dollars | count`
- **`quantity`**: number
- **`unit_cost_usd`**: number (USD per unit)
- **`cost_usd`**: number (quantity * unit_cost_usd; can be repeated for convenience)
- **`labels`**: object (freeform; must include `service` and should include `env`)

Optional fields:

- **`vendor`**: provider name (e.g. `openai`, `github-actions`, `grafana-cloud`)
- **`model`**: LLM model or SKU (if applicable)
- **`request_id`**: request-level correlation (if applicable)
- **`trace_id`**: observability correlation (if available)
- **`notes`**: string

### Example record

```json
{"schema":"economics.ledger.entry.v1","entry_id":"2f0c9c2f-93b2-49ac-b1fd-7c0af3dbbd12","timestamp":"2025-12-21T12:00:00Z","correlation_id":"intent_123","run_id":"ci_456","producer":"ci","category":"compute","unit":"seconds","quantity":120.0,"unit_cost_usd":0.0005,"cost_usd":0.06,"vendor":"github-actions","labels":{"service":"gados-control-plane","env":"test"}}
```

---

## Budget, margin, and trigger rules

### Terms

- **Budget**: maximum allowed spend for a scope (intent, run, day).
- **Margin**: headroom between current spend and budget.
  - \( margin\_usd = budget\_usd - spend\_usd \)
  - \( margin\_pct = (budget\_usd - spend\_usd) / budget\_usd \)

### Scope levels (recommended)

- **Per-intent budget**: applies to all runs under one `correlation_id`.
- **Daily/org budget**: applies to the whole workspace/org per day.

### Trigger thresholds (recommended defaults)

For each scope:

- **WARN** when `spend_usd >= 0.70 * budget_usd`
- **HIGH** when `spend_usd >= 0.90 * budget_usd`
- **CRITICAL** when `spend_usd >= 1.00 * budget_usd`
- **HARD_STOP** when `spend_usd >= 1.10 * budget_usd` (recommended for automated agent loops)

### Trigger semantics

- Thresholds should be evaluated on:
  - each new ledger entry (streaming)
  - and at least daily (batch reconciliation)
- Each trigger emits a notification event with:
  - correlation_id, scope, spend, budget, margin, top contributors by category/vendor

---

## Escalation templates (webhook payloads)

Templates below describe the **body** of notification messages (transport-specific headers configured elsewhere).

### Critical realtime template (budget exceeded)

```json
{
  "schema": "gados.notification.v1",
  "class": "critical_realtime",
  "event_type": "economics.budget_exceeded",
  "correlation_id": "<intent_id>",
  "scope": {"type":"intent","id":"<intent_id>"},
  "summary": "Budget exceeded for intent <intent_id>",
  "facts": {
    "budget_usd": 10.0,
    "spend_usd": 10.7,
    "margin_usd": -0.7,
    "threshold": "HARD_STOP"
  },
  "top_contributors": [
    {"category":"llm","vendor":"<vendor>","cost_usd": 6.2},
    {"category":"compute","vendor":"<vendor>","cost_usd": 3.1}
  ],
  "recommended_actions": [
    "Pause automated agent runs for this correlation_id",
    "Review latest runs and evidence bundle for waste",
    "Adjust budget or reduce scope"
  ]
}
```

### Daily digest template (cost summary)

```json
{
  "schema": "gados.notification.v1",
  "class": "daily_digest",
  "event_type": "economics.daily_summary",
  "scope": {"type":"day","id":"YYYY-MM-DD"},
  "summary": "Daily economics summary",
  "facts": {
    "total_spend_usd": 12.34,
    "intents_over_warn": 3,
    "intents_over_critical": 1
  },
  "top_intents": [
    {"correlation_id":"intent_123","spend_usd": 4.56, "budget_usd": 5.0},
    {"correlation_id":"intent_789","spend_usd": 3.21, "budget_usd": 3.5}
  ]
}
```

