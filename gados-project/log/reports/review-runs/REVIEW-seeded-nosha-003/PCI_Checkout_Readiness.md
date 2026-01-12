# PCI / Checkout Readiness (Beta Checklist)

- [ ] Idempotency for “charge” and “refund” equivalents (no double-spend)
- [ ] Retry storms are bounded (timeouts/backoff) and safe
- [ ] Amount/currency invariants enforced (no negative totals, rounding rules)
- [ ] Audit trail exists for spend guardrails + escalations

