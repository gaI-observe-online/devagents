# Notification Policy

**Status**: Authoritative / Evolves slowly  
**Purpose**: Define when and how the system notifies humans and agents, minimizing interrupts while preserving safety.

## Channels
- **In-app inbox**: Control plane `/inbox` (default, free)
- **Daily digest**: generated report artifacts in `/gados-project/log/reports/` (default, free)
- **CI status**: GitHub Actions checks (default, free)
- **Webhooks** (optional): e.g., Slack/Discord/Teams; configured out-of-band

## Severity and routing
- **INFO**: inbox + digest only
- **WARN**: inbox + digest; optional webhook
- **ERROR**: inbox + digest; webhook recommended
- **CRITICAL**: **immediate** webhook + inbox + digest; if webhook not configured, create escalation artifact

## Batch vs realtime
- **Batch by default**: avoid notification fatigue.
- **Realtime only for CRITICAL** by default.

## Escalation fallback
If a CRITICAL notification cannot be delivered (no webhook configured), the Coordination Agent must create:
- `/gados-project/decision/ESCALATION-###.md`
and record the escalation event in the relevant story log.

## Required artifacts
- Daily digest reports: `/gados-project/log/reports/REPORT-*.md`
- Bus audit log (message send/ack): `/gados-project/log/bus/bus-events.jsonl`

