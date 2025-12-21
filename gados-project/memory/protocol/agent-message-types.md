## Agent-to-agent message types catalog (authoritative)

This catalog defines canonical message types exchanged on the agent bus.

### Envelope (required for all messages)

- **`message_id`**: globally unique ID
- **`type`**: message type (from table below)
- **`version`**: schema version (e.g. `1`)
- **`timestamp`**: ISO-8601 UTC
- **`producer`**: service/agent ID
- **`consumer`**: intended recipient ID or group
- **`correlation_id`**: ties together a story/run (e.g. intent ID)
- **`trace_id`**: observability correlation (optional but recommended)
- **`body`**: type-specific payload
- **`priority`**: `low | normal | high | critical`
- **`ttl_seconds`**: time-to-live for delivery

### Message types (table)

| Type | Producer | Consumer | Required fields (body) | Escalation rules |
|---|---|---|---|---|
| `intent.created` | Human / CA GUI | Control-plane | `intent_id`, `title`, `description`, `owner` | If no `plan.created` within SLA → notify |
| `plan.created` | Control-plane / Planner agent | Artifact store / Inbox | `intent_id`, `plan_id`, `acceptance_criteria`, `evidence_plan` | If AC missing → reject (nack) |
| `work.started` | Agent | Control-plane | `intent_id`, `work_id`, `branch_ref` | If stale heartbeat → notify |
| `artifact.created` | Agent / CI | Artifact store | `artifact_id`, `kind`, `uri`, `sha256` (or content hash) | If write fails → retry with backoff |
| `review.requested` | Control-plane | Reviewer inbox | `intent_id`, `diff_ref`, `summary` | If unassigned beyond SLA → notify |
| `review.recorded` | Reviewer | Control-plane / Artifact store | `intent_id`, `review_id`, `decision`, `notes`, `reviewer_id` | If `changes_requested` → route back to work |
| `validation.requested` | Control-plane | CI / Validator | `intent_id`, `evidence_refs`, `checks` | If missing evidence → reject (nack) |
| `validation.completed` | CI / Validator | Control-plane | `intent_id`, `result`, `check_runs`, `evidence_refs` | If failed → notify + block VERIFIED |
| `vda.decision.recorded` | VDA | Control-plane / Audit log | `intent_id`, `decision`, `rationale`, `evidence_refs`, `vda_id` | If deny → require remediation cycle |
| `status.changed` | Control-plane | Audit log / Inbox | `intent_id`, `from`, `to`, `actor_id`, `reason`, `evidence_refs` | Invalid transition → reject |
| `bus.ack` | Consumer | Durable queue | `message_id`, `consumer`, `received_at` | Missing ack → redeliver |
| `bus.nack` | Consumer | Durable queue / Audit log | `message_id`, `consumer`, `error_code`, `error_detail`, `retryable` | Retryable → redeliver, else escalate |
| `audit.append` | Control-plane / Queue | Audit log | `event_type`, `subject_id`, `data` | Append failure → circuit-breaker + page |

### Nack taxonomy (recommended)

- **`schema_invalid`**: payload failed schema validation (non-retryable)
- **`missing_prerequisite`**: required prior state/evidence missing (retryable only if expected to appear)
- **`permission_denied`**: actor not authorized (non-retryable, escalate)
- **`transient_failure`**: network/temporary backend issue (retryable)

