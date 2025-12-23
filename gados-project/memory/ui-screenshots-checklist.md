## UI screenshots checklist (optional, audit aid)

This checklist defines which UI pages should exist and what each must show. Capture screenshots (or PDFs) for audit evidence when requested.

### Dashboard

- Shows counts by lifecycle state (INTENT/PLANNED/…/VERIFIED)
- Shows alerts summary (critical/high)
- Shows recent activity with timestamps

### Artifacts

- Shows evidence bundle list by `intent_id`
- Each artifact shows: type, URI, hash, created_at, producer
- Immutable reference (content hash or write-once ID)

### Create (Intent creation)

- Create an intent with title/description/owner
- Shows the resulting `intent_id`

### Reports

- Lifecycle compliance report
- SoD compliance report
- Export/download produces an artifact entry

### Inbox

- Shows assigned/unassigned items
- Shows message ack/nack status
- Shows escalation flags (SLA breaches)

### Validate

- Shows validation checks (CI run IDs)
- Shows QA evidence links
- Shows VDA decision controls (approve/deny/defer)
- Shows reason and evidence references for the decision

