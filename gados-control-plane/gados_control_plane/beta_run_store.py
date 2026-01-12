from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .paths import ProjectPaths


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _stamp_compact() -> str:
    # 20251223-002359Z
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%SZ")


def _allocate_beta_run_dir(paths: ProjectPaths, *, scenario: str) -> tuple[str, Path]:
    """
    Create: gados-project/log/reports/beta-runs/BETA-<scenario>-<stamp>-NNN/
    
    Implements retry logic to handle concurrent directory allocation (TOCTOU fix).
    """
    root = paths.gados_root / "log" / "reports" / "beta-runs"
    root.mkdir(parents=True, exist_ok=True)

    # Retry up to 10 times in case of concurrent directory creation
    max_retries = 10
    for retry in range(max_retries):
        base = f"BETA-{scenario}-{_stamp_compact()}"
        n = 1
        for p in root.iterdir():
            if not p.is_dir():
                continue
            name = p.name
            if not name.startswith(base + "-"):
                continue
            tail = name.split("-")[-1]
            if tail.isdigit():
                n = max(n, int(tail) + 1)

        run_id = f"{base}-{n:03d}"
        run_dir = root / run_id
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
            return run_id, run_dir
        except FileExistsError:
            # Another process created this directory concurrently; retry
            if retry == max_retries - 1:
                # Last retry failed, re-raise the exception
                raise
            # Short sleep to allow timestamp to change if needed
            import time
            time.sleep(0.01)
            continue
    
    # This should never be reached due to the raise in the except block
    raise RuntimeError("Failed to allocate beta run directory after retries")


def _write_sha256sums(dir_path: Path) -> None:
    sums: list[str] = []
    for p in sorted(dir_path.rglob("*")):
        if p.is_dir():
            continue
        if p.name == "SHA256SUMS.txt":
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        rel = p.relative_to(dir_path)
        sums.append(f"{h}  {rel}")
    (dir_path / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")


def _check_status(exit_code: int) -> str:
    if exit_code == 0:
        return "PASS"
    if exit_code == 127:
        return "NOT_RUN"
    return "FAIL"


def _compute_confidence(checks: dict[str, dict[str, Any]]) -> tuple[str, list[str]]:
    not_run: list[str] = []
    failed: list[str] = []
    for name, v in (checks or {}).items():
        try:
            rc = int((v or {}).get("exit_code", 127))
        except Exception:
            rc = 127
        st = _check_status(rc)
        if st == "NOT_RUN":
            not_run.append(name)
        elif st == "FAIL":
            failed.append(name)

    # Confidence is primarily evidence completeness.
    if not_run:
        return ("MEDIUM" if len(not_run) <= 2 else "LOW"), not_run
    # If everything ran but some checks failed, confidence is still HIGH (we trust the failure),
    # but the decision will likely be NO-GO/REVIEW.
    return "HIGH", []


@dataclass(frozen=True)
class BetaRunMeta:
    scenario: str
    recommendation: str  # GO | NO-GO | REVIEW
    decision_summary: str
    required_next_action: str
    pm_blockers: list[dict[str, str]]
    top_findings: list[dict[str, Any]]
    evidence_paths: list[str]  # repo-relative paths under gados-project/
    checks: dict[str, dict[str, Any]]  # name -> {"exit_code": int}
    correlation_id: str | None = None


def write_beta_run(paths: ProjectPaths, *, meta: BetaRunMeta) -> dict[str, str]:
    """
    Writes a run-scoped immutable evidence container and a decision artifact:
    - gados-project/log/reports/beta-runs/<run_id>/run.json
    - gados-project/log/reports/beta-runs/<run_id>/SHA256SUMS.txt
    - gados-project/decision/<run_id>.md
    """
    run_id, run_dir = _allocate_beta_run_dir(paths, scenario=meta.scenario)

    confidence, not_run = _compute_confidence(meta.checks)

    run_json = {
        "schema": "gados.beta_run.v1",
        "run_id": run_id,
        "scenario": meta.scenario,
        "generated_at_utc": _utc_now_iso(),
        "recommendation": meta.recommendation,
        "confidence": confidence,
        "not_run": not_run,
        "decision_summary": meta.decision_summary,
        "required_next_action": meta.required_next_action,
        "pm_blockers": meta.pm_blockers,
        "top_findings": meta.top_findings,
        "evidence_paths": meta.evidence_paths,
        "checks": meta.checks,
        "correlation_id": meta.correlation_id,
    }
    (run_dir / "run.json").write_text(json.dumps(run_json, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (run_dir / ".finalized").write_text("finalized\n", encoding="utf-8")
    _write_sha256sums(run_dir)

    # Decision artifact (PM-facing, versioned)
    decision_rel = f"decision/{run_id}.md"
    decision_path = paths.gados_root / decision_rel
    lines: list[str] = []
    lines.append(f"# {run_id}: Beta scenario decision")
    lines.append("")
    lines.append(f"**Generated (UTC)**: {_utc_now_iso()}")
    lines.append(f"**Scenario**: `{meta.scenario}`")
    if meta.correlation_id:
        lines.append(f"**Correlation ID**: `{meta.correlation_id}`")
    lines.append("")
    lines.append(f"## Decision: **{meta.recommendation}**")
    lines.append(f"Confidence: **{confidence}**")
    lines.append("")
    lines.append("## Summary")
    lines.append(meta.decision_summary)
    lines.append("")
    lines.append("## Required next action")
    lines.append(meta.required_next_action)
    lines.append("")
    if meta.pm_blockers:
        lines.append("## Blockers (PM language)")
        for b in meta.pm_blockers:
            lines.append(f"- **{b.get('owner','Eng')}**: {b.get('pm_summary','')}")
        lines.append("")
    if not_run:
        lines.append("## Missing evidence (NOT RUN)")
        for n in not_run:
            lines.append(f"- {n}")
        lines.append("")
    lines.append("## Evidence")
    lines.append(f"- Run metadata: `{(run_dir / 'run.json').relative_to(paths.gados_root)}`")
    lines.append(f"- SHA256SUMS: `{(run_dir / 'SHA256SUMS.txt').relative_to(paths.gados_root)}`")
    for p in meta.evidence_paths:
        lines.append(f"- `{p}`")
    lines.append("")
    decision_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {"run_id": run_id, "run_rel_dir": str(run_dir.relative_to(paths.gados_root)), "decision_rel_path": decision_rel}

