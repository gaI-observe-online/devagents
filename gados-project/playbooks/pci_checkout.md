# PCI / Checkout Playbook (beta, $0)

## Objective
Catch “money-loss” and payment-adjacent failures early with evidence-backed review.

## What to inspect (minimum)
- Idempotency for charge/refund equivalents (no double-spend)
- Amount/currency invariants (no negative totals; rounding rules explicit)
- Retry/timeout behavior (no retry storms; bounded retries)
- Audit trail for economic guardrails and escalations

## Evidence required (copy into review pack)
- Unit/integration test output showing checkout/payment-related tests (or explicit “not present yet”)
- Any config relevant to rate limits, request limits, auth boundaries

## Flag as blockers
- Any path that can create duplicate charges without idempotency keys
- Any logging that might expose payment tokens/secrets

