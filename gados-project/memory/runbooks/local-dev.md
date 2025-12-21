## Runbook: Local development (authoritative)

This runbook describes the expected local workflow for interacting with GADOS.

### Preconditions

- You can access the **Dashboard** (CA GUI).
- You can access the **Inbox** (tasks/messages).
- You can access the **Artifacts** view (evidence and reports).

### Start dashboard

- Open the Dashboard (CA GUI).
- Confirm you can see:
  - Recent intents
  - Items by lifecycle state
  - Alerts/notifications summary

### Run reports

- From “Reports”:
  - Run “Lifecycle compliance” report (states and missing evidence).
  - Run “SoD compliance” report (implementer/reviewer/VDA separation).
  - Export the report as an artifact.

### Use inbox

- Open “Inbox”.
- For a selected `intent_id`:
  - Accept assignment (creates an audit log record).
  - Follow the plan and update status (INTENT → PLANNED → …).
  - Attach artifacts to the intent:
    - plan, diffs, test outputs, QA evidence, review notes

### Validate governance (before asking for VERIFIED)

Use the authoritative rules:

- Lifecycle: `gados-project/memory/lifecycle.md`
- Governance: `gados-project/memory/governance.md`

Checklist:

- Peer review exists and is linked
- Validation evidence exists and is linked
- VDA decision exists and is linked
- Separation-of-duties rules satisfied

### Troubleshooting

- **Missing evidence**: confirm artifacts are stored durably and referenced by URI + hash.
- **Cannot set VERIFIED**: check SoD rules and that VALIDATED prerequisites are met.

