## Notification policy (authoritative)

This policy defines when GADOS emits notifications, which channels to use, and rate limits to avoid alert fatigue.

### Implementation mapping (normative)

This repo’s reference implementation uses:

- **Critical realtime**: webhook delivery **only** for `priority=critical`
- **Daily digest**: all non-critical events are queued and shipped as a single daily digest webhook

### Notification classes

- **Critical realtime**
  - **Goal**: immediate human attention required to prevent loss of auditability or production risk.
  - **Examples**:
    - audit log append failures
    - validator/CI tamper detection
    - unauthorized attempt to set VERIFIED
    - durable queue outage causing message loss risk
  - **Channels** (preferred order):
    - pager / on-call
    - Slack/Teams “alerts” channel
    - email fallback

- **High realtime**
  - **Goal**: timely human attention, but not paging unless persistent.
  - **Examples**:
    - validation failures on main branch
    - repeated nacks for schema/permissions
    - evidence bundle missing past SLA
  - **Channels**:
    - Slack/Teams channel + assignment mention
    - email if unacknowledged within SLA

- **Daily digest**
  - **Goal**: operational visibility without interruption.
  - **Examples**:
    - number of intents created/planned/verified
    - top failing checks
    - longest-running in-progress items
  - **Channels**:
    - email digest
    - dashboard link

### Rate limits (recommended defaults)

- **Critical realtime**: no limit, but deduplicate identical alerts within 2 minutes
- **High realtime**: max 10 per hour per correlation_id
- **Daily digest**: once per day per workspace/org

### Escalation and acknowledgements

- notifications should include:
  - correlation_id / intent_id
  - link to evidence bundle
  - most recent audit log entries
  - recommended action
- human acknowledgement should be recorded as an audit event

---

## Webhook integration configuration (reference implementation)

### Environment variables

- **`GADOS_NOTIFICATIONS_ENABLED`**: `true|false` (default: `true`)
- **`GADOS_WEBHOOK_URL`**: webhook endpoint URL (required to deliver anything)
- **`GADOS_WEBHOOK_SECRET`**: optional HMAC secret for signing webhook payloads
- **`GADOS_DIGEST_STORE_PATH`**: JSONL queue path for digest events (default: `/tmp/gados_digest.jsonl`)
- **`GADOS_DAILY_DIGEST_ENABLED`**: `true|false` (default: `true`)
- **`GADOS_CRITICAL_REALTIME_ENABLED`**: `true|false` (default: `true`)

### Webhook request format

- Method: `POST`
- Content-Type: `application/json`
- Body: JSON payload with schema `gados.notification.v1`
- Optional signature header:
  - `X-GADOS-Signature: sha256=<hex>`
  - computed as HMAC-SHA256 over the raw request body using `GADOS_WEBHOOK_SECRET`

### Payload shape (minimal)

```json
{
  "schema": "gados.notification.v1",
  "class": "critical_realtime|daily_digest",
  "event_type": "string",
  "priority": "low|normal|high|critical",
  "correlation_id": "string|null",
  "subject_id": "string|null",
  "summary": "string",
  "details": {}
}
```

