# PM Walkthrough (Beta+ proof): Clean GO + Seeded NO-GO

Goal: a non-technical PM can understand a release decision in **<2 minutes** using the UI only.

## Preconditions
- Control plane running (golden path):

```bash
cp .env.example .env
make beta-up
```

Open UI: `http://127.0.0.1:8000`

## A) Clean GO walkthrough (expected GO)

**Evidence run**: `REVIEW-local-nosha-003`  
**Expected decision**: **GO**  

### Steps (UI)
1. Open **Beta Runs** (`/beta/runs`)
2. Click run ID `REVIEW-local-nosha-003`
3. Confirm:
   - Decision is **GO**
   - Confidence is shown (HIGH/MEDIUM/LOW)
   - “What ran” table has no **NOT RUN**
   - Evidence links open (Executive summary, Findings.csv, SHA256SUMS)

### Screenshot checklist
- Run list (showing run ID + decision)
- Run detail (Decision + Confidence + Required next action)
- Evidence pack (Executive summary opened in `/view`)

### PM decision prompt (copy/paste)
“System reports **GO** with HIGH confidence and complete evidence. Approve release unless business context requires extra review.”

## B) Seeded NO-GO walkthrough (expected NO-GO)

This proves an **irreversible NO-GO path** that cannot be bypassed without explicit Human Authority sign-off.

### Seed the failure (one file)
Create a temporary file containing a private key marker (do **not** commit):

```bash
cat > app/_seeded_secret_for_beta_proof.txt <<'EOF'
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDJs4D0uS4zS1Z/
-----END PRIVATE KEY-----
EOF
```

Run the review pack:

```bash
REVIEW_RUN_KEY=seeded-nosha python scripts/generate_review_pack.py || true
```

**Evidence runs** (determinism proof):
- `REVIEW-seeded-nosha-002` (NO-GO)
- `REVIEW-seeded-nosha-003` (NO-GO, same blocker count)

**Expected decision**: **NO-GO**  
**Expected blocker**: “Secrets detected (1)”  

### Steps (UI)
1. Open **Beta Runs** (`/beta/runs`)
2. Click run ID `REVIEW-seeded-nosha-003`
3. Confirm:
   - Decision is **NO-GO**
   - Summary says release blocked by automated gates
   - Top finding includes `SECRET:Private Key` with evidence file path
   - Required next action explains fix vs override
   - Override is shown as required and is created only with explicit name/role/reason

### Screenshot checklist
- Run list with the seeded run showing **NO-GO**
- Run detail showing:
  - NO-GO + blocker summary (PM language)
  - Top finding showing secret detection evidence path
  - Override form (name/role/reason)

### Clean up (remove seed)
```bash
rm -f app/_seeded_secret_for_beta_proof.txt
```

### PM decision prompt (copy/paste)
“System reports **NO-GO**: hardcoded credential/secret detected. Release is blocked until removed and rotated, or explicitly overridden by Human Authority with justification.”

## Non-scope (Beta+ boundary)
- This system is **not** legal certification, compliance attestation, or production monitoring.
- It is an **evidence-backed decision control plane** for governed delivery workflows.

