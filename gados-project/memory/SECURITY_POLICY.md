# Security Policy (Control Plane)

**Status**: Authoritative / Evolves slowly  
**Purpose**: Prevent governance bypass and protect artifact integrity.

## Threat model (minimum)
The control plane can:
- create/update versioned artifacts
- append audit logs
- enqueue/ack agent bus messages

If exposed without access control, an attacker can:
- forge roles (e.g., impersonate `DeliveryGovernor` or `HumanAuthority`)
- write unauthorized story log events
- create/modify ADRs and decisions
- spam/poison the agent bus

## Access control requirement
All **write actions** MUST require authentication.

**Write actions include**:
- `POST /create/*` (epic/story/change/adr)
- `POST /append/story-log`
- `POST /bus/send`
- `POST /bus/ack`
- `POST /agents/run/*` (agent runs that write artifacts)

## Auth mechanism (MVP)
Use HTTP Basic auth with environment variables:
- `GADOS_BASIC_AUTH_USER`
- `GADOS_BASIC_AUTH_PASSWORD`

If these are unset, the server may run in **insecure local mode** (developer convenience),
but must not be deployed publicly in that configuration.

## Audit attribution
For every write action, the system should record:
- authenticated username (e.g., `submitted_by`)
- timestamp (UTC)
in the relevant audit trail (story log / bus log / ADR artifact).

## Deployment guidance
- Run behind HTTPS in any non-local environment.
- Do not expose the control plane publicly without auth.
- Prefer network-level restrictions (VPN/allowlist) in addition to app auth.

