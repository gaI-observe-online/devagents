# Agent-to-Agent Communication Protocol

**Status**: Authoritative / Evolves slowly  
**Purpose**: Define how virtual agents communicate with delivery guarantees and auditable logging.

## Principles
- **Durable delivery**: messages are stored until acknowledged.
- **Idempotency**: senders provide `idempotency_key` to prevent duplicate effects.
- **Traceability**: every message is logged to an append-only audit log with correlation IDs.
- **Separation of duties**: protocol supports routing without allowing scope/verification bypass.

## Message envelope (v1)
All agent-to-agent messages MUST include:

- `schema`: `gados.bus.message.v1`
- `message_id`: UUID
- `idempotency_key`: string (sender-chosen; stable for retries)
- `created_at`: ISO-8601 UTC
- `from`:
  - `role`: e.g. `CoordinationAgent`, `QAAgent`, `PeerReviewer`, `DeliveryGovernor`, `StrategicBrain`
  - `agent_id`: string (virtual agent instance id)
- `to`:
  - `role`: role name
  - `agent_id`: string or `*` (broadcast within role)
- `type`: message type (e.g. `REPORT_REQUESTED`, `EVIDENCE_READY`, `VERIFY_REQUESTED`, `ESCALATION_OPENED`)
- `severity`: `INFO` | `WARN` | `ERROR` | `CRITICAL`
- `correlation_id`: UUID (ties a conversation/workflow together)
- `story_id` (optional): `STORY-###`
- `epic_id` (optional): `EPIC-###`
- `artifact_refs` (optional): list of artifact paths
- `payload`: JSON object

## Delivery semantics
- **At-least-once delivery** until `ACK`.
- **ACK states**:
  - `ACKED` (processed successfully)
  - `NACKED` (failed; will retry unless `dead_lettered=true`)
- **Retry policy**: exponential backoff; after max retries, message is **dead-lettered**.

## Audit logging
Each message send + each ACK/NACK MUST be appended to:
- `/gados-project/log/bus/bus-events.jsonl`

Each line is a JSON object (append-only). Corrections are appended as new events.

