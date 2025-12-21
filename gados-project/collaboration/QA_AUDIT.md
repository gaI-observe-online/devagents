## QA audit checks (verbatim evidence)

Date: 2025-12-21

Purpose: keep a **shared, auditable** record of how we capture both **success** and **failure** outputs for regression checks.

> Note: “FAIL examples” below are **controlled simulations** that do not change code and are immediately reverted, solely to demonstrate evidence capture format.

---

## PASS evidence

### Lint (ruff)

```bash
python3 -m ruff check .
All checks passed!
```

### Unit tests (pytest)

```bash
python3 -m pytest -q
.................                                                        [100%]
17 passed in 0.46s
```

### Artifact validator

```bash
python3 gados-control-plane/scripts/validate_artifacts.py
artifact_validation=PASS
```

---

## FAIL evidence (controlled simulations)

### Artifact validator FAIL example (missing required artifact)

Simulation method:

- Temporarily moved `gados-project/memory/COMM_PROTOCOL.md` out of the repo, ran the validator, then restored it.

```bash
bash -lc 'mv gados-project/memory/COMM_PROTOCOL.md /tmp/COMM_PROTOCOL.md && (python3 gados-control-plane/scripts/validate_artifacts.py || true) ; mv /tmp/COMM_PROTOCOL.md gados-project/memory/COMM_PROTOCOL.md'
artifact_validation=FAIL
missing=gados-project/memory/COMM_PROTOCOL.md
```

### Pytest “failure-mode” example (no tests selected)

This demonstrates how a non-successful run is recorded even when no code is changed.

```bash
bash -lc 'python3 -m pytest -q -k does_not_exist || true'

17 deselected in 0.41s
```

