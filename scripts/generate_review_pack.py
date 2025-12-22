from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _run(cmd: list[str]) -> tuple[int, str]:
    """
    Run a command and return (exit_code, combined_output).
    Never raises; meant for CI report generation.
    """
    try:
        p = subprocess.run(cmd, check=False, capture_output=True, text=True)  # noqa: S603
        out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
        return int(p.returncode), out.strip()
    except Exception as e:
        return 127, f"ERROR running {cmd!r}: {e}"


def _run_to_file(cmd: list[str], out_file: Path) -> int:
    """
    Run a command and write combined stdout/stderr to out_file.
    Returns exit code.
    """
    try:
        p = subprocess.run(cmd, check=False, capture_output=True, text=True)  # noqa: S603
        out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
        out_file.write_text(out, encoding="utf-8")
        return int(p.returncode)
    except Exception as e:
        out_file.write_text(f"ERROR running {cmd!r}: {e}\n", encoding="utf-8")
        return 127


def _safe_json_load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _severity_rank(sev: str) -> int:
    sev = (sev or "").upper()
    return {"LOW": 10, "MEDIUM": 20, "HIGH": 30, "CRITICAL": 40}.get(sev, 10)


def _load_policy(repo_root: Path) -> dict[str, Any]:
    # Optional policy file; fall back to strict defaults.
    try:
        import yaml
    except Exception:
        return {}

    p = repo_root / "gados-project" / "memory" / "REVIEW_FACTORY_POLICY.yaml"
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = Path(os.getenv("REVIEW_PACK_DIR", "review-pack")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = out_dir / "Evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    pr = os.getenv("GITHUB_PR_NUMBER", "").strip()
    sha = os.getenv("GITHUB_SHA", "").strip()
    ref = os.getenv("GITHUB_REF", "").strip()
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()

    policy = _load_policy(repo_root)

    # Build & Test Verifier Agent
    ruff_rc = _run_to_file(["python", "-m", "ruff", "check", "."], evidence_dir / "ruff.txt")
    pytest_rc = _run_to_file(["python", "-m", "pytest", "-q", "-m", "not integration"], evidence_dir / "pytest_unit.txt")
    validator_rc = _run_to_file(
        ["python", "gados-control-plane/scripts/validate_artifacts.py"], evidence_dir / "governance_validator.txt"
    )

    # SAST Agent (Bandit)
    bandit_json_path = out_dir / "SAST_Report.json"
    bandit_rc = _run_to_file(
        ["python", "-m", "bandit", "-q", "-r", "app", "gados-control-plane/gados_control_plane", "-f", "json"],
        bandit_json_path,
    )

    # SCA Agent (pip-audit) + SBOM
    sca_json_path = out_dir / "SCA_Report.json"
    pip_audit_rc = _run_to_file(["python", "-m", "pip_audit", "-r", "requirements.txt", "-f", "json"], sca_json_path)

    sbom_path = out_dir / "SBOM.cyclonedx.json"
    sbom_rc = _run_to_file(
        ["python", "-m", "pip_audit", "-r", "requirements.txt", "-f", "cyclonedx-json"], sbom_path
    )

    # Secrets & Config Hygiene Agent (detect-secrets)
    secrets_json_path = out_dir / "Secrets_Report.json"
    secrets_rc = _run_to_file(
        ["detect-secrets", "scan", "--all-files"],
        secrets_json_path,
    )

    summary = {
        "generated_at_utc": _utc_now_iso(),
        "repo": repo,
        "ref": ref,
        "sha": sha,
        "pr": pr,
        "checks": {
            "ruff": {"exit_code": ruff_rc},
            "pytest_unit": {"exit_code": pytest_rc},
            "validator": {"exit_code": validator_rc},
            "sast_bandit": {"exit_code": bandit_rc},
            "sca_pip_audit": {"exit_code": pip_audit_rc},
            "sbom_cyclonedx": {"exit_code": sbom_rc},
            "secrets_detect_secrets": {"exit_code": secrets_rc},
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Parse findings
    findings: list[dict[str, Any]] = []

    # Bandit findings -> Findings.csv rows
    bandit_obj = _safe_json_load(bandit_json_path)
    if isinstance(bandit_obj, dict):
        for issue in bandit_obj.get("results", []) or []:
            if not isinstance(issue, dict):
                continue
            sev = str(issue.get("issue_severity", "LOW")).upper()
            cwe = ""
            cwe_obj = issue.get("issue_cwe") or {}
            if isinstance(cwe_obj, dict) and cwe_obj.get("id"):
                cwe = f"CWE-{cwe_obj.get('id')}"
            findings.append(
                {
                    "id": f"BANDIT:{issue.get('test_id')}",
                    "severity": sev,
                    "tool": "bandit",
                    "component": "app/control-plane",
                    "file": issue.get("filename", ""),
                    "line": issue.get("line_number", ""),
                    "title": issue.get("issue_text", ""),
                    "cwe": cwe,
                    "owasp_top10": "A03:2021" if cwe else "",
                    "asvs": "V1" if cwe else "",
                    "pci_dss": "6" if cwe else "",
                    "nist_ssdf": "PW.4" if cwe else "",
                    "owner": "",
                    "status": "OPEN",
                }
            )

    # pip-audit findings -> Findings.csv rows
    sca_obj = _safe_json_load(sca_json_path)
    sca_vuln_count = 0
    if isinstance(sca_obj, dict):
        deps = sca_obj.get("dependencies") or []
        if isinstance(deps, list):
            for dep in deps:
                if not isinstance(dep, dict):
                    continue
                vulns = dep.get("vulns") or []
                if not isinstance(vulns, list):
                    continue
                for v in vulns:
                    if not isinstance(v, dict):
                        continue
                    sca_vuln_count += 1
                    vid = str(v.get("id") or "VULN")
                    findings.append(
                        {
                            "id": f"SCA:{vid}",
                            "severity": "HIGH",
                            "tool": "pip-audit",
                            "component": str(dep.get("name") or "dependency"),
                            "file": "requirements.txt",
                            "line": "",
                            "title": str(v.get("description") or vid),
                            "cwe": "",
                            "owasp_top10": "A06:2021",
                            "asvs": "V14",
                            "pci_dss": "6",
                            "nist_ssdf": "PW.4",
                            "owner": "",
                            "status": "OPEN",
                        }
                    )

    # detect-secrets findings -> Findings.csv rows
    secrets_obj = _safe_json_load(secrets_json_path)
    secret_count = 0
    if isinstance(secrets_obj, dict):
        results = secrets_obj.get("results") or {}
        if isinstance(results, dict):
            for file, items in results.items():
                if not isinstance(items, list):
                    continue
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    secret_count += 1
                    findings.append(
                        {
                            "id": f"SECRET:{it.get('type')}",
                            "severity": "CRITICAL",
                            "tool": "detect-secrets",
                            "component": "repo",
                            "file": file,
                            "line": it.get("line_number", ""),
                            "title": "Potential secret detected",
                            "cwe": "CWE-798",
                            "owasp_top10": "A02:2021",
                            "asvs": "V14",
                            "pci_dss": "3",
                            "nist_ssdf": "PW.4",
                            "owner": "",
                            "status": "OPEN",
                        }
                    )

    # Write Findings.csv
    findings_csv = out_dir / "Findings.csv"
    cols = [
        "id",
        "severity",
        "tool",
        "component",
        "file",
        "line",
        "title",
        "cwe",
        "owasp_top10",
        "asvs",
        "pci_dss",
        "nist_ssdf",
        "owner",
        "status",
    ]
    with findings_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in findings:
            w.writerow({k: row.get(k, "") for k in cols})

    # Coordinator / Auditor: compute go/no-go
    gates = (policy.get("gates") or {}) if isinstance(policy, dict) else {}
    secrets_block = bool(((gates.get("secrets") or {}).get("block_on_findings")) if isinstance(gates, dict) else True)
    sca_block = bool(((gates.get("sca") or {}).get("block_on_vulnerabilities")) if isinstance(gates, dict) else True)
    sast_floor = str(((gates.get("sast") or {}).get("block_on_severity_at_or_above")) if isinstance(gates, dict) else "HIGH")
    gov_block = bool(((gates.get("governance") or {}).get("block_on_failure")) if isinstance(gates, dict) else True)

    max_sast = "LOW"
    for fnd in findings:
        if fnd.get("tool") == "bandit" and _severity_rank(str(fnd.get("severity", "LOW"))) > _severity_rank(max_sast):
            max_sast = str(fnd.get("severity", "LOW")).upper()

    blocked_reasons: list[str] = []
    if gov_block and validator_rc != 0:
        blocked_reasons.append("Governance validator failed")
    if secrets_block and secret_count > 0:
        blocked_reasons.append(f"Secrets detected ({secret_count})")
    if sca_block and sca_vuln_count > 0:
        blocked_reasons.append(f"Vulnerable dependencies detected ({sca_vuln_count})")
    if _severity_rank(max_sast) >= _severity_rank(sast_floor):
        blocked_reasons.append(f"SAST findings at/above {sast_floor} (max={max_sast})")

    recommendation = "GO" if not blocked_reasons else "NO-GO"

    # Pack: Executive summary + domain checklists + repro template
    (out_dir / "Executive_Summary.md").write_text(
        "\n".join(
            [
                "# Executive Summary",
                "",
                f"**Generated (UTC)**: {_utc_now_iso()}",
                f"**Repo**: `{repo}`",
                (f"**PR**: `{pr}`" if pr else ""),
                (f"**SHA**: `{sha}`" if sha else ""),
                "",
                f"## Release recommendation: **{recommendation}**",
                "",
                "### Blockers",
                *(["- (none)"] if not blocked_reasons else [f"- {r}" for r in blocked_reasons]),
                "",
                "### Top risks (from Findings.csv)",
                "- Review `Findings.csv` sorted by severity/tool.",
                "",
            ]
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (out_dir / "PCI_Checkout_Readiness.md").write_text(
        "\n".join(
            [
                "# PCI / Checkout Readiness (Beta Checklist)",
                "",
                "- [ ] Idempotency for “charge” and “refund” equivalents (no double-spend)",
                "- [ ] Retry storms are bounded (timeouts/backoff) and safe",
                "- [ ] Amount/currency invariants enforced (no negative totals, rounding rules)",
                "- [ ] Audit trail exists for spend guardrails + escalations",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    (out_dir / "Privacy_Log_Redaction_Check.md").write_text(
        "\n".join(
            [
                "# Privacy / Log Redaction Check (Beta Checklist)",
                "",
                "- [ ] No secrets in repo (see Secrets_Report.json)",
                "- [ ] No PII in logs by default (verify control-plane logs + bus audit log)",
                "- [ ] Correlation IDs are used instead of raw sensitive values",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    (out_dir / "Threat_Model_Update.md").write_text(
        "\n".join(
            [
                "# Threat Model Update (Deltas)",
                "",
                "_Beta factory auto-generated stub._",
                "",
                "- New trust boundaries: (fill in)",
                "- New data flows: (fill in)",
                "- New attacker goals: (fill in)",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    (out_dir / "Repro_Steps.md").write_text(
        "\n".join(
            [
                "# Reproduction Steps (Top Issues)",
                "",
                "For each top finding in `Findings.csv`, add minimal reproduction steps here.",
                "",
                "## Finding <ID>",
                "- Steps:",
                "- Expected:",
                "- Actual:",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    # Human-friendly index
    (out_dir / "REVIEW_PACK.md").write_text(
        "\n".join(
            [
                "# Review Pack Index",
                "",
                f"**Generated (UTC)**: {_utc_now_iso()}",
                "",
                "## Files",
                "- `Executive_Summary.md`",
                "- `Findings.csv`",
                "- `SAST_Report.json`",
                "- `SCA_Report.json`",
                "- `SBOM.cyclonedx.json`",
                "- `Secrets_Report.json`",
                "- `PCI_Checkout_Readiness.md`",
                "- `Privacy_Log_Redaction_Check.md`",
                "- `Threat_Model_Update.md`",
                "- `Repro_Steps.md`",
                "- `Evidence/` (raw logs: ruff/pytest/validator)",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    # Optional immutability/traceability: write SHA256SUMS for the pack.
    sums_path = out_dir / "SHA256SUMS.txt"
    sums: list[str] = []
    for p in sorted(out_dir.rglob("*")):
        if p.is_dir():
            continue
        if p.name == "SHA256SUMS.txt":
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        rel = p.relative_to(out_dir)
        sums.append(f"{h}  {rel}")
    sums_path.write_text("\n".join(sums) + "\n", encoding="utf-8")

    print(f"Wrote review pack: {out_dir}")
    return 1 if blocked_reasons else 0


if __name__ == "__main__":
    raise SystemExit(main())

