from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph


class AuditState(TypedDict, total=False):
    pr_ref: str
    repo_path: str
    out_dir: str
    changed_files: List[str]
    tool_outputs: Dict[str, str]  # name -> filepath
    findings: List[Dict[str, Any]]
    notes: List[str]


def run_cmd(cmd: List[str], cwd: str | None = None) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)  # noqa: S603
    out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
    return int(p.returncode), out


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8") or "null")
    except Exception:
        return None


def _severity_rank(sev: str) -> int:
    sev = (sev or "").upper()
    return {"LOW": 10, "MEDIUM": 20, "HIGH": 30, "CRITICAL": 40}.get(sev, 10)


def ingest_node(state: AuditState) -> AuditState:
    repo = Path(state["repo_path"]).resolve()
    out = Path(state["out_dir"]).resolve()
    ensure_dir(out)
    ensure_dir(out / "Tool_Outputs")

    # Minimal: list changed files vs origin/main...HEAD (works in CI and local with origin/main present)
    rc, diff = run_cmd(["git", "diff", "--name-only", "origin/main...HEAD"], cwd=str(repo))
    if rc != 0:
        # Fallback to HEAD~1..HEAD for local-only repos
        rc2, diff2 = run_cmd(["git", "diff", "--name-only", "HEAD~1..HEAD"], cwd=str(repo))
        diff = diff2 if rc2 == 0 else diff
    changed = [f.strip() for f in diff.splitlines() if f.strip()]
    state["changed_files"] = changed
    state.setdefault("notes", []).append(f"Changed files: {len(changed)}")
    return state


def secrets_scan_node(state: AuditState) -> AuditState:
    repo = Path(state["repo_path"]).resolve()
    out = Path(state["out_dir"]).resolve() / "Tool_Outputs"
    report = out / "secrets_detect_secrets.json"

    rc, out_text = run_cmd(["detect-secrets", "scan", "--all-files"], cwd=str(repo))
    write_text(report, out_text)
    state.setdefault("tool_outputs", {})["secrets"] = str(report)
    state.setdefault("notes", []).append(f"Secrets scan exit_code={rc}")
    return state


def sast_node(state: AuditState) -> AuditState:
    repo = Path(state["repo_path"]).resolve()
    out = Path(state["out_dir"]).resolve() / "Tool_Outputs"
    report = out / "sast_bandit.json"

    # Bandit JSON output. Non-zero can mean issues or errors; keep artifact either way.
    rc, out_text = run_cmd(
        ["python", "-m", "bandit", "-q", "-r", "app", "gados-control-plane/gados_control_plane", "-f", "json"],
        cwd=str(repo),
    )
    write_text(report, out_text)
    state.setdefault("tool_outputs", {})["sast"] = str(report)
    state.setdefault("notes", []).append(f"SAST(Bandit) exit_code={rc}")
    return state


def sca_sbom_node(state: AuditState) -> AuditState:
    repo = Path(state["repo_path"]).resolve()
    out = Path(state["out_dir"]).resolve() / "Tool_Outputs"
    sca = out / "sca_pip_audit.json"
    sbom = out / "sbom_cyclonedx.json"

    rc1, sca_text = run_cmd(["python", "-m", "pip_audit", "-r", "requirements.txt", "-f", "json"], cwd=str(repo))
    write_text(sca, sca_text)

    rc2, sbom_text = run_cmd(["python", "-m", "pip_audit", "-r", "requirements.txt", "-f", "cyclonedx-json"], cwd=str(repo))
    write_text(sbom, sbom_text)

    state.setdefault("tool_outputs", {})["sca"] = str(sca)
    state.setdefault("tool_outputs", {})["sbom"] = str(sbom)
    state.setdefault("notes", []).append(f"SCA(pip-audit) exit_code={rc1}; SBOM exit_code={rc2}")
    return state


def dast_lite_node(state: AuditState) -> AuditState:
    state.setdefault("notes", []).append("DAST-lite skipped (configure and run separately).")
    return state


@dataclass(frozen=True)
class _Finding:
    Finding_ID: str
    Title: str
    Severity: str  # Critical/High/Medium/Low
    Mapping: List[str]
    Evidence: str
    Impact: str
    Recommendation: str
    Human_Review_Required: str  # yes/no
    Notes: str = ""

    def to_row(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d["Mapping"] = ";".join(self.Mapping)
        return d


def pci_checkout_iva_node(state: AuditState) -> AuditState:
    """
    Deterministic IVA (no LLM): interpret evidence outputs and apply a few strict rules.
    """
    repo = Path(state["repo_path"]).resolve()
    tool = state.get("tool_outputs", {})
    findings: List[Dict[str, Any]] = state.get("findings", [])

    # Required artifacts check (beta minimal set we can actually generate here)
    required = [
        ("Secrets scan report", tool.get("secrets")),
        ("SAST report", tool.get("sast")),
        ("SCA report", tool.get("sca")),
        ("SBOM", tool.get("sbom")),
    ]
    for name, fp in required:
        if not fp or not Path(fp).exists():
            findings.append(
                _Finding(
                    Finding_ID="EVIDENCE-MISSING-001",
                    Title=f"Missing required evidence: {name}",
                    Severity="High",
                    Mapping=["ASVS:V1", "NIST:PW.8"],
                    Evidence=str(fp or ""),
                    Impact="Audit decision cannot be made without required evidence artifacts.",
                    Recommendation="Run the missing tool and attach raw output to the audit pack.",
                    Human_Review_Required="yes",
                ).to_row()
            )

    # Secrets: CRITICAL if any findings
    secrets_path = Path(tool.get("secrets", "")) if tool.get("secrets") else None
    if secrets_path and secrets_path.exists():
        obj = _read_json(secrets_path)
        secret_count = 0
        if isinstance(obj, dict):
            results = obj.get("results") or {}
            if isinstance(results, dict):
                for _file, items in results.items():
                    if isinstance(items, list):
                        secret_count += len(items)
        if secret_count > 0:
            findings.append(
                _Finding(
                    Finding_ID="SEC-SECRET-001",
                    Title="Secrets detected by detect-secrets",
                    Severity="Critical",
                    Mapping=["OWASP:A02:2021", "CWE-798", "PCI:3", "ASVS:V14", "NIST:PW.4"],
                    Evidence=str(secrets_path),
                    Impact="Compromise risk. Secrets must be removed and rotated immediately.",
                    Recommendation="Remove secrets, rotate credentials, and add/maintain a secrets scanning gate.",
                    Human_Review_Required="yes",
                ).to_row()
            )

    # SCA: HIGH if any vulns
    sca_path = Path(tool.get("sca", "")) if tool.get("sca") else None
    vuln_count = 0
    if sca_path and sca_path.exists():
        obj = _read_json(sca_path)
        if isinstance(obj, dict) and isinstance(obj.get("dependencies"), list):
            for dep in obj["dependencies"]:
                if isinstance(dep, dict) and isinstance(dep.get("vulns"), list):
                    vuln_count += len(dep["vulns"])
    if vuln_count > 0:
        findings.append(
            _Finding(
                Finding_ID="SCA-VULN-001",
                Title="Vulnerable dependencies detected (pip-audit)",
                Severity="High",
                Mapping=["OWASP:A06:2021", "PCI:6", "ASVS:V14", "NIST:PW.4"],
                Evidence=str(sca_path),
                Impact="Known vulnerabilities may be exploitable; requires remediation or justified exception.",
                Recommendation="Upgrade dependencies and document mitigations/exceptions in the review pack.",
                Human_Review_Required="yes",
                Notes=f"vuln_count={vuln_count}",
            ).to_row()
        )

    # Simple checkout trust heuristic (seeded demo): flag if changed files contain client-trusted totals
    patterns = [
        r'request\.json\[\s*["\']total["\']\s*\]',
        r'order_total\s*=\s*request\.json',
        r'total\s*=\s*request\.json',
    ]
    for rel in state.get("changed_files", []):
        p = (repo / rel).resolve()
        try:
            if not p.is_file():
                continue
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in patterns:
            if __import__("re").search(pat, txt):
                findings.append(
                    _Finding(
                        Finding_ID="CHECKOUT-TOTAL-TRUST-001",
                        Title="Potential checkout integrity bug: server trusts client-submitted totals",
                        Severity="High",
                        Mapping=["OWASP:A04:2021", "CWE-345", "PCI:6"],
                        Evidence=f"{rel} (pattern={pat})",
                        Impact="Money-loss risk via price/discount tampering.",
                        Recommendation="Recompute totals server-side; validate discounts server-side; add tests.",
                        Human_Review_Required="yes",
                    ).to_row()
                )
                break

    state["findings"] = findings
    state.setdefault("notes", []).append("PCI/Checkout IVA completed (deterministic).")
    # Include playbook path for humans
    playbook = repo / "gados-project" / "playbooks" / "pci_checkout.md"
    if playbook.exists():
        state.setdefault("notes", []).append(f"Playbook: {playbook}")
    return state


def coordinator_node(state: AuditState) -> AuditState:
    out = Path(state["out_dir"]).resolve()
    pack = out / "audit-pack"
    ensure_dir(pack)
    ensure_dir(pack / "Tool_Outputs")
    ensure_dir(pack / "Evidence")

    # Copy tool outputs into pack
    tool_outputs = state.get("tool_outputs", {})
    for _name, fp in tool_outputs.items():
        p = Path(fp)
        if p.exists():
            dest = pack / "Tool_Outputs" / p.name
            write_text(dest, p.read_text(encoding="utf-8"))

    # Findings register (CSV)
    findings = state.get("findings", [])
    findings_csv = pack / "Findings_Register.csv"
    cols = [
        "Finding_ID",
        "Title",
        "Severity",
        "Mapping",
        "Evidence",
        "Impact",
        "Recommendation",
        "Human_Review_Required",
        "Notes",
    ]
    with findings_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in findings:
            w.writerow({k: row.get(k, "") for k in cols})

    # Control matrix (minimal)
    matrix_csv = pack / "Control_Matrix.csv"
    with matrix_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Control", "Evidence", "Status"])
        w.writerow(["Secrets scanning", "Tool_Outputs/secrets_detect_secrets.json", "PASS/FAIL (see findings)"])
        w.writerow(["SAST", "Tool_Outputs/sast_bandit.json", "PASS/FAIL (see findings)"])
        w.writerow(["SCA", "Tool_Outputs/sca_pip_audit.json", "PASS/FAIL (see findings)"])
        w.writerow(["SBOM", "Tool_Outputs/sbom_cyclonedx.json", "GENERATED"])

    # Scope/context
    scope_md = pack / "Scope_and_Context.md"
    scope_lines = [
        "# Scope and Context",
        "",
        f"PR Ref: `{state.get('pr_ref', 'local')}`",
        f"Repo: `{state.get('repo_path', '.')}`",
        "",
        "## Changed files",
        *([f"- `{p}`" for p in state.get("changed_files", [])] or ["- (none detected)"]),
        "",
        "## Notes",
        *([f"- {n}" for n in state.get('notes', [])] or ["- (none)"]),
        "",
    ]
    write_text(scope_md, "\n".join(scope_lines))

    # Executive summary
    crit = [f for f in findings if str(f.get("Severity", "")).lower() == "critical"]
    high = [f for f in findings if str(f.get("Severity", "")).lower() == "high"]
    decision = "NO-GO" if (crit or high) else "GO (Beta)"
    exec_md = pack / "Executive_Summary.md"
    top = (crit + high)[:10]
    exec_lines = [
        "# Executive Summary",
        "",
        f"Decision: **{decision}**",
        f"Changed files: {len(state.get('changed_files', []))}",
        f"Critical: {len(crit)} | High: {len(high)} | Total findings: {len(findings)}",
        "",
        "## Top findings",
        *([f"- [{t.get('Finding_ID')}] {t.get('Title')} ({t.get('Severity')}) Evidence: {t.get('Evidence')}" for t in top] or ["- (none)"]),
        "",
    ]
    write_text(exec_md, "\n".join(exec_lines))

    # Reviewer signoff
    signoff = pack / "Reviewer_Signoff.md"
    write_text(
        signoff,
        "\n".join(
            [
                "# Reviewer Sign-off",
                "Reviewer Name:",
                "Date:",
                "Decision: [GO / NO-GO / GO with Exceptions]",
                "",
                "Notes:",
                "- ",
                "",
            ]
        ),
    )

    # Optional immutability/traceability: write SHA256SUMS for the audit-pack.
    sums: list[str] = []
    sums_path = pack / "SHA256SUMS.txt"
    for p in sorted(pack.rglob("*")):
        if p.is_dir():
            continue
        if p.name == "SHA256SUMS.txt":
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        rel = p.relative_to(pack)
        sums.append(f"{h}  {rel}")
    write_text(sums_path, "\n".join(sums) + "\n")

    state.setdefault("notes", []).append(f"Audit pack written to: {pack}")
    return state


def build_graph():
    g = StateGraph(AuditState)
    g.add_node("ingest", ingest_node)
    g.add_node("secrets", secrets_scan_node)
    g.add_node("sast", sast_node)
    g.add_node("sca_sbom", sca_sbom_node)
    g.add_node("dast_lite", dast_lite_node)
    g.add_node("pci_checkout_iva", pci_checkout_iva_node)
    g.add_node("coordinator", coordinator_node)

    g.set_entry_point("ingest")
    g.add_edge("ingest", "secrets")
    g.add_edge("secrets", "sast")
    g.add_edge("sast", "sca_sbom")
    g.add_edge("sca_sbom", "dast_lite")
    g.add_edge("dast_lite", "pci_checkout_iva")
    g.add_edge("pci_checkout_iva", "coordinator")
    g.add_edge("coordinator", END)
    return g.compile()


def main() -> int:
    repo_path = os.environ.get("REPO_PATH", ".")
    out_dir = os.environ.get("OUT_DIR", "./audit_run")
    pr_ref = os.environ.get("PR_REF", "local")

    graph = build_graph()
    graph.invoke({"repo_path": repo_path, "out_dir": out_dir, "pr_ref": pr_ref})

    pack = Path(out_dir).resolve() / "audit-pack"
    print("Done. Audit pack at:", pack)
    print("Decision summary:", pack / "Executive_Summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

