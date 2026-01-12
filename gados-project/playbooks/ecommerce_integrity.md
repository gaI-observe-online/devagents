# E-commerce Integrity Playbook (beta, $0)

## Objective
Catch “must-not-fail” integrity issues with deterministic evidence.

## Domains
- Payments / money movement
- Pricing / discounts
- AuthN/AuthZ boundaries
- Abuse / fraud controls (rate limits, idempotency)
- Uptime / health signaling

## Evidence required
- Review pack outputs (SAST/SCA/SBOM/secrets + test logs)
- If present: integration smoke evidence and readiness/health outputs

## Blockers
- Secrets detected
- Vulnerable dependencies without mitigation plan
- SAST HIGH findings without fix/justification
- Any path that can cause double-spend or privilege escalation

