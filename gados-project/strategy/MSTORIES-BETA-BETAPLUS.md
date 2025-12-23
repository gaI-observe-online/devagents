## mSTORIES: Beta → Beta+ (capability milestones + acceptance criteria)

This document captures the authoritative Beta→Beta+ scope as **milestone stories (mStories)** with acceptance criteria.  
It is intended for PM/QA/Dev Agents to execute and verify.

> Important: this file describes **target scope**.  
> Current implementation evidence is tracked separately in:
> - `gados-project/collaboration/STATUS.md`
> - `gados-project/verification/BETA-QA-evidence.md`

---

# 🟦 BETA (Baseline – “System is Real”)

> **Goal:** Prove the system works, enforces rules, and produces evidence.

### mStory B1 — Enforced Governance Decisions

**As a** delivery system  
**I must** enforce GO / NO-GO decisions based on explicit policy  
**So that** releases cannot bypass governance rules.

**Acceptance Criteria**

- Validator enforces decision outcomes
- NO-GO blocks pipeline deterministically
- Override requires explicit role & reason
- CI fails on violation

**Status:** ✅ DONE (target)

---

### mStory B2 — Scenario Execution (Core 3)

**As a** control plane  
**I must** execute defined beta scenarios  
**So that** risk categories are covered.

**Scenarios**

- Spend Guardrail
- Policy Drift
- SLA Sentinel

**Acceptance Criteria**

- Each scenario runs end-to-end
- Each produces a decision artifact
- Each emits evidence into reports

**Status:** ✅ DONE (target)

---

### mStory B3 — Evidence Generation

**As an** audit system  
**I must** produce immutable evidence per run  
**So that** decisions are defensible.

**Acceptance Criteria**

- Append-only ledger
- Run-scoped artifacts
- Manifest generated per run
- Evidence survives re-runs

**Status:** ✅ DONE (target)

---

### mStory B4 — CI as a Gate

**As a** delivery workflow  
**I must** enforce quality and policy checks in CI  
**So that** bad changes cannot merge.

**Acceptance Criteria**

- CI runs lint + tests
- CI runs validator
- CI blocks merge on failure
- CI artifacts downloadable

**Status:** ✅ DONE (target)

---

### mStory B5 — Minimal Decision UI

**As a** PM or reviewer  
**I must** see decisions and evidence without CLI access  
**So that** I can make release decisions.

**Acceptance Criteria**

- Dashboard shows decisions
- Inbox shows pending reviews
- Reports and artifacts accessible
- Read-only access sufficient

**Status:** ✅ DONE (target)

---

# 🟩 BETA+ (Trust & Operability – “System Can Be Used”)

> **Goal:** Make the system safe, explainable, and usable under real pressure.

### mStory B+1 — Decision Explainability

**As a** PM  
**I must** understand *why* a decision was made  
**So that** I can defend it to leadership.

**Acceptance Criteria**

- Each decision includes:
  - risk summary
  - business impact
  - required action
- No raw-only technical language

**Status:** 🔄 IN PROGRESS / PARTIAL (target)

---

### mStory B+2 — Accountable Override

**As a** delivery governor  
**I may** override a decision with justification  
**So that** real-world exceptions are handled safely.

**Acceptance Criteria**

- Override requires:
  - name
  - role
  - reason
- Override recorded in evidence
- Override visible in UI

**Status:** 🔄 PARTIAL (target)

---

### mStory B+3 — PM-First Experience

**As a** non-technical PM  
**I must** reach a decision in under 2 minutes  
**So that** the system doesn’t slow delivery.

**Acceptance Criteria**

- Decision summary page
- Clear GO / NO-GO indicator
- “What to do next” visible
- No architecture knowledge required

**Status:** 🔄 PARTIAL (target)

---

### mStory B+4 — Failure Transparency

**As a** reviewer  
**I must** see what failed and what didn’t run  
**So that** missing data doesn’t masquerade as success.

**Acceptance Criteria**

- Explicit “NOT RUN” markers
- Clear failure reasons
- No silent passes

**Status:** ⏳ PLANNED / LIGHT WORK (target)

---

### mStory B+5 — Confidence Signaling

**As a** PM  
**I must** know how confident the system is  
**So that** I apply the right level of scrutiny.

**Acceptance Criteria**

- Confidence level per decision: HIGH / MEDIUM / LOW
- Confidence based on evidence completeness
- Displayed in UI

**Status:** ⏳ PLANNED (target)

---

### mStory B+6 — Explicit Non-Scope Declaration

**As a** stakeholder  
**I must** see what the system does *not* certify  
**So that** it is not misused.

**Acceptance Criteria**

- UI + docs state:
  - Not legal certification
  - Not compliance attestation
  - Not production monitoring

**Status:** ⏳ PLANNED (target)

---

# 🔵 OUT OF SCOPE (Explicitly NOT Beta+)

These are future v1+, not Beta+:

- Auto-remediation
- External audit certification
- RBAC expansion
- SaaS multi-tenancy
- Live production hooks
- ML-based risk scoring

