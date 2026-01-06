# OWASP ASVS (L2) Playbook (beta, $0)

## Objective
Provide a lightweight ASVS-aligned review lens for web APIs.

## Evidence required
- SAST output (Bandit/Semgrep if added later)
- SCA output + SBOM
- Secrets scan output
- Auth/config defaults review (env contract)

## Minimum ASVS areas to cover (beta)
- V1 Architecture / design notes (threat model delta stub OK)
- V2 Authentication (write/admin endpoints, session management)
- V3 Session management (cookie flags if cookies exist; token handling)
- V4 Access control (default deny on write/admin)
- V5 Validation (input size limits, parsing)
- V10 Logging (no secrets/PII, trace correlation)
- V14 Configuration (secure defaults, no debug in prod)

