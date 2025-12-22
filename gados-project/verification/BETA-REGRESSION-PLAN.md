## BETA regression plan (inputs → expectations → evidence)

This plan is written as **inputs → expectations → evidence** and is intended to be executed and pasted into `BETA-QA-evidence.md`.

### Preconditions (offline / zero-cost)

- No paid APIs
- No outbound network calls required for the core pipeline
- Deterministic results: same input → same findings/decision

---

## Stage 1 — Code change introduced

- **Inputs**: PR/branch with known changes (seeded scenarios below)
- **Expectations**:
  - Changed files are identified
  - Scope is recorded (systems impacted)
- **Evidence**:
  - `audit-pack/` includes a scope/manifest entry (or equivalent)
  - Verbatim console output showing changed file list

---

## Stage 2 — Ingestion

- **Inputs**: repository checkout + diff range
- **Expectations**:
  - Pipeline records which subsystems are in scope (payments/security/privacy/auth)
- **Evidence**:
  - Evidence pack includes an ingestion record (file list + scope tags)

---

## Stage 3 — Deterministic tool execution

Tools required (minimum):

- Secrets scan
- SAST
- SCA + SBOM
- (Optional) DAST-lite

- **Inputs**: repo snapshot
- **Expectations**:
  - Tool execution is deterministic and produces raw outputs
  - No tool invents findings (facts only)
- **Evidence**:
  - `audit-pack/Tool_Outputs/*` contains raw outputs (verbatim)
  - Logs show tool versions and commands used

---

## Stage 4 — Specialist IVA analysis

IVAs required (minimum):

- PCI/Checkout IVA
- Security/OWASP IVA
- Privacy IVA

- **Inputs**: raw tool outputs + relevant code context
- **Expectations**:
  - IVAs explain evidence and map to OWASP/CWE/PCI readiness
  - IVAs do not invent vulnerabilities beyond tool facts
  - Missing evidence is flagged “Needs Human Review”
- **Evidence**:
  - IVA findings reference specific tool outputs and code locations
  - Findings include severity, remediation, and “Needs Human Review” flags

---

## Stage 5 — Coordinator / auditor

- **Inputs**: all findings from tools + IVAs
- **Expectations**:
  - Findings deduplicated and normalized
  - Policy gates applied (GO / NO-GO)
- **Evidence**:
  - Evidence pack includes the decision logic outcome and rationale
  - Findings register shows normalized severities and dedupe notes

---

## Stage 6 — Audit evidence pack generated (required output validation)

Expected structure:

```
audit-pack/
 ├─ 00_Executive_Summary.md
 ├─ 03_Findings_Register.(json/csv)
 ├─ Tool_Outputs/
 │   ├─ secrets_scan
 │   ├─ sast
 │   ├─ sbom
 │   └─ sca
 └─ 06_Reviewer_Signoff.md
```

Executive summary must include:

- GO / NO-GO decision
- counts of Critical / High findings
- references to evidence files

---

## Policy gates (assertions)

### NO-GO if any

- Hardcoded secret detected
- PAN/CVV handling or logging detected
- Known exploitable CVE in auth/payment path
- Missing authorization on refund/admin endpoints

### GO (Beta) only if all

- No Critical or High findings
- Evidence pack complete
- Human sign-off file present

---

## Required seeded QA scenarios

Each scenario must produce **inputs → expectations → evidence** and include a GO/NO-GO assertion.

1) **Seeded vulnerability: hardcoded secret**
   - Expect: NO-GO
   - Evidence: secrets scan output + finding register + executive summary NO-GO

2) **Seeded vulnerability: vulnerable dependency**
   - Expect: NO-GO
   - Evidence: SCA/SBOM output + CVE reference + executive summary NO-GO

3) **Seeded vulnerability: trust client order total**
   - Expect: High severity
   - Evidence: IVA finding referencing code path + mapping to OWASP/CWE

4) **Clean run**
   - Expect: GO (Beta) and complete evidence pack
   - Evidence: executive summary GO + zero critical/high

5) **Missing evidence**
   - Expect: “Needs Human Review”
   - Evidence: IVA flags missing DFD/logs/redaction evidence

6) **Repeatability**
   - Expect: same inputs → same findings/decision
   - Evidence: two run IDs with identical findings register hash (or identical content)

---

## Swimlane reference (expectation vs reality)

- `gados-project/verification/EXPECTATION-VS-REALITY.md`

