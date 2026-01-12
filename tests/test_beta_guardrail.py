from pathlib import Path

from gados_control_plane.beta_spend_guardrail import run_daily_spend_guardrail
from gados_control_plane.paths import ProjectPaths


def test_daily_spend_guardrail_creates_escalation_and_messages(tmp_path: Path, monkeypatch):
    # Minimal fake project tree
    repo_root = tmp_path / "repo"
    gados_root = repo_root / "gados-project"
    templates_dir = gados_root / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (gados_root / "decision").mkdir(parents=True, exist_ok=True)
    (gados_root / "log" / "economics").mkdir(parents=True, exist_ok=True)

    # Provide the escalation template
    (templates_dir / "ESCALATION.template.md").write_text(
        "# ESCALATION-###: <Title>\n\n**Date (UTC)**: <YYYY-MM-DD>\n\n## Summary\nWhat decision is needed and why was it escalated?\n",
        encoding="utf-8",
    )

    # Isolate runtime/audit outputs
    runtime_dir = tmp_path / "runtime"
    audit_dir = tmp_path / "audit"
    monkeypatch.setenv("GADOS_RUNTIME_DIR", str(runtime_dir))
    monkeypatch.setenv("GADOS_AUDIT_DIR", str(audit_dir))

    paths = ProjectPaths(repo_root=repo_root, gados_root=gados_root, templates_dir=templates_dir)
    out = run_daily_spend_guardrail(paths=paths, budget_usd=10.0, spend_steps_usd=[4.0, 4.0, 3.0], scope_id="2025-12-22")

    assert out.threshold is not None
    assert out.escalation_rel_path is not None
    assert (gados_root / out.escalation_rel_path).exists()

    # Ledger appended
    ledger_path = gados_root / "log" / "economics" / "ledger.jsonl"
    assert ledger_path.exists()
    assert len(ledger_path.read_text(encoding="utf-8").strip().splitlines()) >= 1

    # Bus audit log written via env override
    bus_audit = audit_dir / "bus-events.jsonl"
    assert bus_audit.exists()
    assert "MESSAGE_SENT" in bus_audit.read_text(encoding="utf-8")

    # Notification queued via runtime dir
    queue_path = runtime_dir / "notifications.queue.jsonl"
    assert queue_path.exists()
    assert "economics.budget_threshold" in queue_path.read_text(encoding="utf-8")

