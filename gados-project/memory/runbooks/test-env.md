## Runbook: Test environment (authoritative)

This runbook describes the expected test-environment workflow for GADOS verification.

### Preconditions

- A test environment exists (ephemeral or shared).
- The repository provides make targets (or equivalent scripts) to bring up and smoke-test the environment.

### Bring up the test environment

Run:

```bash
make test-env-up
```

Expected result:

- Environment endpoints are reachable
- A run ID (or deployment ID) is printed and stored as an artifact

### Run smoke tests

Run:

```bash
make test-smoke
```

Required evidence:

- Command output stored as an artifact
- Any screenshots/videos stored as artifacts

### Run full test suite

Run:

```bash
make test
```

Required evidence:

- CI run ID or local run logs preserved
- Test report artifacts attached (JUnit/coverage if applicable)

### If any step fails

- Record failure details as an artifact (logs, screenshots).
- Create or update `validation.completed` evidence records.
- Do not request VERIFIED until failures are resolved and re-validated.

