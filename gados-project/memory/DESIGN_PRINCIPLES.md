# DESIGN PRINCIPLES (Authoritative Memory)

**Status**: Authoritative / Changes are rare  
**Purpose**: The core constraints that shape all planning, implementation, verification, and operations.

## 1) Cardinal rule: artifacts are truth
If it is not written in a versioned artifact, it does not exist.

## 2) Truth over speed
- A feature is **not** complete until verified with evidence.
- “Works on my machine” and subjective claims are insufficient.

## 3) Separation of powers (single responsibility enforcement)
Each agent has exactly **one job** and must not encroach on others:

- **Execution Engine (Vibe)**: implement approved change plans + tests only.
- **QA Agent**: collect evidence only.
- **Peer Reviewer**: quality/architecture assessment only.
- **Coordination Agent (CA)**: orchestration, artifact management, routing, reporting only.
- **Delivery Governor (VDA)**: verification decision + certification only.
- **Human Authority**: ethics, risk, pricing approvals, escalations only.

## 4) Verification independence
The implementer cannot be the verifier.
Evidence and review must be independently produced and then adjudicated by VDA.

## 5) Economics first
Pricing and architecture decisions must be driven by:
- usage and cost data (feature-level where possible)
- explicit margin thresholds
- documented rationale in artifacts

## 6) Audit-ready always
Every decision, escalation, and verification outcome must be traceable to:
- a story spec
- an approved change plan
- an evidence package
- a decision record (if escalated)
- an append-only audit log entry

## 7) Minimize human interrupts
Escalations should be tiered:
- auto-resolve where safe
- route to Strategic Brain where appropriate
- escalate to Human Authority only for high-risk decisions

