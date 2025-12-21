## Notification policy (authoritative)

This policy defines when GADOS emits notifications, which channels to use, and rate limits to avoid alert fatigue.

### Notification classes

- **Critical realtime**
  - **Goal**: immediate human attention required to prevent loss of auditability or production risk.
  - **Examples**:
    - Audit log append failures
    - Validator/CI tamper detection
    - Unauthorized attempt to set VERIFIED
    - Durable queue outage causing message loss risk
  - **Channels** (preferred order):
    - Pager / on-call
    - Slack/Teams “alerts” channel
    - Email fallback

- **High realtime**
  - **Goal**: timely human attention, but not paging unless persistent.
  - **Examples**:
    - Validation failures on main branch
    - Repeated nacks for schema/permissions
    - Evidence bundle missing past SLA
  - **Channels**:
    - Slack/Teams channel + assignment mention
    - Email if unacknowledged within SLA

- **Daily digest**
  - **Goal**: operational visibility without interruption.
  - **Examples**:
    - Number of intents created/planned/verified
    - Top failing checks
    - Longest-running in-progress items
  - **Channels**:
    - Email digest
    - Dashboard link

### Rate limits (recommended defaults)

- **Critical realtime**: no limit, but deduplicate identical alerts within 2 minutes
- **High realtime**: max 10 per hour per correlation_id
- **Daily digest**: once per day per workspace/org

### Escalation and acknowledgements

- Notifications should include:
  - correlation_id / intent_id
  - link to evidence bundle
  - most recent audit log entries
  - recommended action
- Human acknowledgement should be recorded as an audit event.

