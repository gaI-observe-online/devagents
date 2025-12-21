## Notification policy (authoritative)

This policy defines when GADOS emits notifications, which channels to use, and rate limits to avoid alert fatigue.

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

