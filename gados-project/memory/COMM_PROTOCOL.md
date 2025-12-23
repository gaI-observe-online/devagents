## Communication protocol (authoritative)

This document defines the agent-to-agent and control-plane messaging protocol used by GADOS (envelope, delivery semantics, message types, and error handling).

### Envelope (required for all messages)

- **`message_id`**: globally unique ID
- **`type`**: message type (see catalog)
- **`version`**: schema version (e.g. `1`)
- **`timestamp`**: ISO-8601 UTC
- **`producer`**: service/agent ID
- **`consumer`**: intended recipient ID or group
- **`correlation_id`**: ties together a story/run (e.g. intent ID)
- **`trace_id`**: observability correlation (optional but recommended)
- **`priority`**: `low | normal | high | critical`
- **`ttl_seconds`**: time-to-live for delivery
- **`body`**: type-specific payload

### Delivery semantics (agent bus)

- **Durable queue**: messages are persisted before delivery.
- **Inbox**: consumers pull/receive messages and process them idempotently.
- **Ack**: consumer confirms successful processing.
- **Nack**: consumer indicates failure, with retryability flag.
- **Audit log**: send/ack/nack must be appended as immutable audit events.

### Message types catalog

| Type | Producer | Consumer | Required fields (body) | Escalation rules |
|---|---|---|---|---|
| `intent.created` | Human / CA GUI | Control-plane | `intent_id`, `title`, `description`, `owner` | If no `plan.created` within SLA → notify |
| `plan.created` | Control-plane / Planner agent | Artifact store / Inbox | `intent_id`, `plan_id`, `acceptance_criteria`, `evidence_plan` | If AC missing → nack |
| `work.started` | Agent | Control-plane | `intent_id`, `work_id`, `branch_ref` | If stale heartbeat → notify |
| `artifact.created` | Agent / CI | Artifact store | `artifact_id`, `kind`, `uri`, `content_hash` | If write fails → retry with backoff |
| `review.requested` | Control-plane | Reviewer inbox | `intent_id`, `diff_ref`, `summary` | If unassigned beyond SLA → notify |
| `review.recorded` | Reviewer | Control-plane | `intent_id`, `review_id`, `decision`, `notes`, `reviewer_id` | If `changes_requested` → route back to work |
| `validation.requested` | Control-plane | CI / Validator | `intent_id`, `evidence_refs`, `checks` | If missing evidence → nack |
| `validation.completed` | CI / Validator | Control-plane | `intent_id`, `result`, `check_runs`, `evidence_refs` | If failed → notify + block VERIFIED |
| `vda.decision.recorded` | VDA | Control-plane | `intent_id`, `decision`, `rationale`, `evidence_refs`, `vda_id` | If deny → remediation cycle |
| `status.changed` | Control-plane | Audit log / Inbox | `intent_id`, `from`, `to`, `actor_id`, `reason`, `evidence_refs` | Invalid transition → nack |
| `bus.ack` | Consumer | Durable queue | `message_id`, `consumer`, `received_at` | Missing ack → redeliver |
| `bus.nack` | Consumer | Durable queue / Audit log | `message_id`, `consumer`, `error_code`, `error_detail`, `retryable` | Retryable → redeliver; else escalate |
| `audit.append` | Control-plane / Queue | Audit log | `event_type`, `subject_id`, `data` | Append failure → page |

### Nack taxonomy (recommended)

- **`schema_invalid`**: payload failed schema validation (non-retryable)
- **`missing_prerequisite`**: prior state/evidence missing (retryable only if expected to appear)
- **`permission_denied`**: actor not authorized (non-retryable; notify)
- **`transient_failure`**: network/temporary backend issue (retryable)

