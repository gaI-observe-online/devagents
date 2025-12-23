## BETA QA evidence package (TEMPLATE)

Date: YYYY-MM-DD  
Repo: `<org>/<repo>`  
PR(s) under test: `#<n>` (or branch)  
Commit under test: `<sha>`

### Environment

OS / Kernel:

```bash
uname -a
<paste output>
```

Python / tooling:

```bash
python3 --version
<paste output>

python3 -m pip --version
<paste output>

python3 -m ruff --version
<paste output>

python3 -m pytest --version
<paste output>
```

Docker:

```bash
docker --version
<paste output or mark BLOCKED>
```

---

## Acceptance criteria (beta)

Define ACs for each target workflow at minimum:

- **AC-CP-1 (control-plane smoke)**
- **AC-BUS-1 (bus)**
- **AC-NOTIF-1 (notifications)**
- **AC-ECO-1 (economics)**
- **AC-VAL-1 (validator gate)**
- **AC-INT-1 (docker/integration)**
- **AC-PIP-1 (pipeline stages)**: ingestion → tools → IVA → coordinator → audit pack
- **AC-POL-1 (policy gates)**: GO/NO-GO rules enforced from evidence
- **AC-OFF-1 (offline/zero-cost)**: no outbound calls; no paid APIs; deterministic outputs

---

## Commands run (verbatim) + outputs (verbatim)

### Static + unit

```bash
python -m ruff check .
<paste output>
```

```bash
python -m pytest -q
<paste output>
```

```bash
python gados-control-plane/scripts/validate_artifacts.py
<paste output or mark FAIL/BLOCKED with reason>
```

### Docker / integration (requires Docker-capable machine)

```bash
make test-env-up
<paste output or mark BLOCKED with reason>
```

```bash
curl -fsS http://localhost:3000/api/health
<paste output or mark BLOCKED with reason>
```

```bash
curl -fsS http://localhost:8000/health
<paste output or mark BLOCKED with reason>
```

```bash
make test-smoke
<paste output or mark BLOCKED with reason>
```

Tempo trace verification (service.name="gados-control-plane"):

1) <step 1>
2) <step 2>
Screenshot: (optional) `<path or link>`

```bash
make test
<paste output or mark BLOCKED with reason>
```

```bash
make test-env-down
<paste output or mark BLOCKED with reason>
```

---

## Evidence mapped to acceptance criteria

| AC | Result (PASS/FAIL/BLOCKED) | Evidence links (files/URLs/log excerpts) |
|---|---|---|
| AC-CP-1 |  |  |
| AC-BUS-1 |  |  |
| AC-NOTIF-1 |  |  |
| AC-ECO-1 |  |  |
| AC-VAL-1 |  |  |
| AC-INT-1 |  |  |
| AC-PIP-1 |  |  |
| AC-POL-1 |  |  |
| AC-OFF-1 |  |  |

---

## Notes / blockers

- If any step is BLOCKED, state the exact reason and the required environment to unblock it.

## Regression plan references

- Regression plan: `gados-project/verification/BETA-REGRESSION-PLAN.md`
- Evidence pack checklist: `gados-project/verification/BETA-EVIDENCE-PACK-CHECKLIST.md`

