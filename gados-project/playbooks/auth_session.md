# Auth / Session Playbook (beta, $0)

## Objective
Ensure safe defaults and clear boundaries for write/admin capabilities.

## Evidence required
- Config contract (`.env.example`)
- Endpoint list (at minimum: what endpoints write artifacts / mutate state)

## Checks (minimum)
- Write endpoints require auth when credentials are configured
- Auth failures are audit-logged
- Rate limiting and request size caps enabled
- CORS policy is explicit (no wildcard unless intentional)

