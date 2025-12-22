## Audit evidence pack validation checklist (inputs → expectations → evidence)

Purpose: QA validates that each run produces a complete, human-reviewable audit pack.

### Inputs

- A completed pipeline run (for a specific PR/commit)
- Output directory (or artifact link) for the audit pack

### Expectations (must hold)

- Audit pack directory exists and is readable offline
- Executive summary contains GO/NO-GO and references
- Findings register exists and matches tool outputs
- Tool outputs are preserved verbatim
- Reviewer signoff template exists

### Evidence (what QA must capture)

- Directory listing (verbatim)
- File hashes (optional but recommended)
- Screenshots (optional) of key files opened in a viewer

---

## Required structure (must exist)

```
audit-pack/
 ├─ 00_Executive_Summary.md
 ├─ 03_Findings_Register.(json/csv)
 ├─ Tool_Outputs/
 │   ├─ secrets_scan/
 │   ├─ sast/
 │   ├─ sbom/
 │   └─ sca/
 └─ 06_Reviewer_Signoff.md
```

---

## File-by-file checks

### 00_Executive_Summary.md

- Must include:
  - GO / NO-GO decision
  - counts of Critical / High
  - list of evidence references (paths)
  - “Needs Human Review” flags (if any)

### 03_Findings_Register.(json/csv)

- Must include columns/fields at minimum:
  - id, title, severity, category (tool/IVA), evidence_ref, remediation, needs_human_review
- Must be consistent with tool outputs:
  - each finding references a corresponding raw tool output or code reference

### Tool_Outputs/*

- Must include:
  - tool name + version
  - the exact command invocation (if available)
  - raw output content without modification

### 06_Reviewer_Signoff.md

- Must include:
  - reviewer name/role/date
  - signoff decision (approve/deny)
  - rationale and references to the executive summary/findings register

