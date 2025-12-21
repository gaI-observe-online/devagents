## Decisions log (append-only)

Record governance and collaboration decisions here for auditability.

### Template (copy/paste)

```
Date:
Decision:
Context:
Options considered:
Chosen option + rationale:
Owner:
Links (PR/commit/docs):
```

### Entries

#### 2025-12-21 — Docs as “versioned artifacts”

- **Decision**: Consolidate GADOS docs into a small set of stable, versioned artifact files (ARCHITECTURE/RUNBOOKS/COMM_PROTOCOL/NOTIFICATION_POLICY/VERIFICATION_POLICY).
- **Context**: Reduce merge conflicts and ambiguity for audits; enable dashboard to link directly to a stable set of docs.
- **Options considered**:
  - Many small docs across nested folders
  - A few consolidated “artifact” docs (chosen)
- **Owner**: Agent
- **Links**:
  - `gados-project/strategy/ARCHITECTURE.md`
  - `gados-project/strategy/RUNBOOKS.md`
  - `gados-project/memory/COMM_PROTOCOL.md`
  - `gados-project/memory/NOTIFICATION_POLICY.md`
  - `gados-project/memory/VERIFICATION_POLICY.md`

#### 2025-12-21 — Move Docker/integration regression to CI

- **Decision**: Run Docker/integration smoke checks in CI (GitHub Actions) since some environments (e.g., this agent runner) do not have Docker.
- **Context**: Local QA remains blocked without Docker; we still need auditable integration evidence.
- **Chosen option + rationale**: Add an `integration` CI job that starts `docker compose`, starts the service, and runs smoke curls against Grafana and `/health`.
- **Owner**: QA agent
- **Links**:
  - `.github/workflows/blank.yml` (`integration` job)

