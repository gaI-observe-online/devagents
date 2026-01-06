# Privacy / PII Playbook (beta, $0)

## Objective
Prevent PII leakage through logs, traces, and artifacts.

## Evidence required
- Secrets scan output
- Example runtime logs (control-plane + bus audit log)

## Checks (minimum)
- No secrets committed; no tokens/passwords in `.env.example`
- Logs avoid raw PII; use correlation IDs instead
- Trace/log correlation uses `request_id`/trace IDs, not sensitive payloads

