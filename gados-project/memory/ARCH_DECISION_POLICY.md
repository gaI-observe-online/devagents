# Architecture Decision Policy

**Status**: Authoritative / Evolves slowly  
**Purpose**: Ensure **Human Authority** can influence (and approve) re-architecture and high-risk architecture changes.

## When Human Authority approval is required
Human Authority must approve an **Architecture Decision Record (ADR)** when a change is:
- **Re-architecture** (changes core components, data model, interfaces, or major dependencies)
- **Irreversible** (hard-to-rollback migrations, breaking API changes, vendor lock-in)
- **Security/privacy-impacting** (PII flows, auth, encryption, access control)
- **Economics-impacting** (material cost increase, pricing model change, margin floor risk)

## Required artifact: ADR
Any decision in the categories above must be captured as an ADR:
- `gados-project/decision/ADR-###.md`

Use the template:
- `gados-project/templates/ADR.template.md`

## Change plan linkage
If a story requires an ADR:
- The approved change plan (`CHANGE-###-*.yaml`) must reference the ADR in its notes/links.
- The story log must include an event referencing the ADR artifact.

## Control plane behavior (expected)
- Provide a UI path for humans to **review and approve** ADRs.
- Provide a quick “request ADR approval” flow that routes a bus message to `HumanAuthority` inbox.
- CI/governance validation should ensure required policy artifacts exist (and later: enforce ADR references for flagged stories).

