from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from opentelemetry import trace

from app.economics import LedgerEntry, append_ledger_entry, build_budget_trigger_event
from app.notifications import Notification, dispatch_notification

from .beta_run_store import BetaRunMeta, write_beta_run
from .bus import send_message
from .paths import ProjectPaths


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class GuardrailResult:
    correlation_id: str
    scope_id: str
    budget_usd: float
    spend_usd: float
    threshold: str | None
    ledger_rel_path: str
    escalation_rel_path: str | None
    bus_message_id: str | None
    notification_queued_path: str | None


def _severity_from_threshold(threshold: str) -> str:
    # Map economics thresholds to bus/notification severities.
    return {
        "WARN": "WARN",
        "HIGH": "ERROR",
        "CRITICAL": "CRITICAL",
        "HARD_STOP": "CRITICAL",
    }.get(threshold, "INFO")


_ESC_RE = re.compile(r"^ESCALATION-(\d{3})\.md$")


def _next_escalation_id(decision_dir: Path) -> str:
    decision_dir.mkdir(parents=True, exist_ok=True)
    nums: list[int] = []
    for p in decision_dir.iterdir():
        if not p.is_file():
            continue
        m = _ESC_RE.match(p.name)
        if m:
            nums.append(int(m.group(1)))
    n = (max(nums) + 1) if nums else 1
    return f"ESCALATION-{n:03d}"


def _render_escalation_md(*, template: str, esc_id: str, title: str, severity: str, body: str) -> str:
    today = datetime.now(UTC).date().isoformat()
    out = template
    out = out.replace("ESCALATION-###", esc_id)
    out = out.replace("<Title>", title)
    out = out.replace("<YYYY-MM-DD>", today)
    out = out.replace("LOW | MEDIUM | HIGH | CRITICAL", severity)
    out = out.replace("<name>", "CoordinationAgent")
    # Put a short, concrete summary near the top.
    out = out.replace("What decision is needed and why was it escalated?", body)
    return out


def run_daily_spend_guardrail(
    *,
    paths: ProjectPaths,
    budget_usd: float,
    spend_steps_usd: list[float] | None = None,
    scope_id: str | None = None,
    correlation_id: str | None = None,
) -> GuardrailResult:
    """
    Beta scenario: simulate spend accumulation, append ledger entries, and on threshold breach:
    - create an ESCALATION decision artifact
    - emit a bus message (in-app inbox)
    - queue a notification (digest flush)
    """
    tracer = trace.get_tracer("gados-control-plane")
    corr = correlation_id or str(uuid.uuid4())
    scope = scope_id or datetime.now(UTC).date().isoformat()
    steps = spend_steps_usd or [budget_usd * 0.4, budget_usd * 0.4, budget_usd * 0.3]

    ledger_path = paths.gados_root / "log" / "economics" / "ledger.jsonl"
    ledger_rel = str(ledger_path.relative_to(paths.gados_root))

    entries: list[LedgerEntry] = []
    message_id: str | None = None
    esc_rel: str | None = None
    queued_path: str | None = None
    threshold: str | None = None

    with tracer.start_as_current_span("beta.daily_spend_guardrail") as span:
        span.set_attribute("gados.correlation_id", corr)
        span.set_attribute("gados.scope_id", scope)
        span.set_attribute("gados.budget_usd", float(budget_usd))

        run_id = str(uuid.uuid4())
        for i, amount in enumerate(steps):
            amt = float(amount)
            with tracer.start_as_current_span("beta.spend_step") as step_span:
                step_span.set_attribute("step.index", i)
                step_span.set_attribute("step.spend_usd", amt)

                e = LedgerEntry(
                    correlation_id=corr,
                    run_id=run_id,
                    producer="agent",
                    category="llm",
                    unit="dollars",
                    quantity=amt,
                    unit_cost_usd=1.0,
                    labels={"scenario": "daily_spend_guardrail", "scope_id": scope, "step": i},
                    vendor="simulated",
                    model="simulated",
                    request_id=None,
                    trace_id=None,
                    notes=f"beta guardrail spend step {i}",
                )
                append_ledger_entry(e, path=str(ledger_path))
                entries.append(e)

                trig = build_budget_trigger_event(
                    entries=entries,
                    budget_usd=float(budget_usd),
                    scope_type="day",
                    scope_id=scope,
                    correlation_id=corr,
                )
                if trig and esc_rel is None:
                    threshold = str(trig.get("facts", {}).get("threshold", "CRITICAL"))
                    severity = _severity_from_threshold(threshold)
                    span.set_attribute("gados.threshold", threshold)

                    # Create escalation decision artifact (audit-ready)
                    esc_id = _next_escalation_id(paths.gados_root / "decision")
                    tpl = (paths.templates_dir / "ESCALATION.template.md").read_text(encoding="utf-8")
                    title = f"Economics threshold {threshold} reached (daily spend guardrail)"
                    body = (
                        f"Budget threshold reached.\n\n"
                        f"- correlation_id: `{corr}`\n"
                        f"- scope: `day/{scope}`\n"
                        f"- threshold: **{threshold}**\n"
                        f"- spend_usd: {trig.get('facts', {}).get('spend_usd')}\n"
                        f"- budget_usd: {trig.get('facts', {}).get('budget_usd')}\n"
                        f"- generated_at_utc: {_utc_now_iso()}\n"
                    )
                    esc_md = _render_escalation_md(
                        template=tpl,
                        esc_id=esc_id,
                        title=title,
                        severity="CRITICAL" if severity in {"ERROR", "CRITICAL"} else "HIGH",
                        body=body,
                    )
                    esc_path = paths.gados_root / "decision" / f"{esc_id}.md"
                    esc_path.write_text(esc_md, encoding="utf-8")
                    esc_rel = str(esc_path.relative_to(paths.gados_root))

                    # Bus message (visible in Inbox UI)
                    message_id = send_message(
                        from_role="EconomicsAgent",
                        from_agent_id="ECO-1",
                        to_role="CoordinationAgent",
                        to_agent_id="CA-1",
                        type="economics.budget_threshold",
                        severity=severity,  # type: ignore[arg-type]
                        correlation_id=corr,
                        artifact_refs=[esc_rel],
                        payload=trig,  # includes facts + top_contributors
                    )

                    # Notification queue (visible after digest flush)
                    nr = dispatch_notification(
                        Notification(
                            type="economics.budget_threshold",
                            severity=severity,  # type: ignore[arg-type]
                            correlation_id=corr,
                            artifact_refs=[esc_rel],
                            payload={"trigger": trig},
                        )
                    )
                    queued_path = str(nr.get("queued_path")) if nr else None

        spend_total = float(sum(e.cost_usd() for e in entries))
        span.set_attribute("gados.spend_usd", spend_total)

    return GuardrailResult(
        correlation_id=corr,
        scope_id=scope,
        budget_usd=float(budget_usd),
        spend_usd=float(sum(e.cost_usd() for e in entries)),
        threshold=threshold,
        ledger_rel_path=ledger_rel,
        escalation_rel_path=esc_rel,
        bus_message_id=message_id,
        notification_queued_path=queued_path,
    )


def write_guardrail_beta_run(*, paths: ProjectPaths, result: GuardrailResult) -> dict[str, str]:
    """
    Beta+ standard: emit a run-scoped decision object + immutable run folder.
    """
    thr = (result.threshold or "").upper()
    if thr in {"CRITICAL", "HARD_STOP"}:
        rec = "NO-GO"
        summary = "Budget threshold breached at critical level. Release blocked until spend is understood and controlled."
        next_action = "Review the escalation artifact, reduce spend, and re-run guardrail after remediation."
        pm_blockers = [{"owner": "Eng+PM", "pm_summary": "Spend exceeded approved budget threshold; release blocked until mitigated."}]
        sev = "CRITICAL"
    elif thr in {"WARN", "HIGH"}:
        rec = "REVIEW"
        summary = "Budget threshold warning detected. Release requires review before proceeding."
        next_action = "Review spend drivers and confirm budget approval before release."
        pm_blockers = [{"owner": "PM", "pm_summary": "Spend warning requires approval; confirm budget and proceed with caution."}]
        sev = "HIGH" if thr == "HIGH" else "WARN"
    else:
        rec = "GO"
        summary = "No budget threshold breach detected."
        next_action = "Proceed with release; continue monitoring spend."
        pm_blockers = []
        sev = "INFO"

    checks = {
        "ledger_appended": {"exit_code": 0 if result.ledger_rel_path else 1},
        "escalation_created": {"exit_code": 0 if result.escalation_rel_path else 1},
        "bus_event_emitted": {"exit_code": 0 if result.bus_message_id else 1},
        "notification_queued": {"exit_code": 0 if result.notification_queued_path else 1},
    }
    # Dynamically find the most recent notification file for today's date
    today_str = datetime.now(UTC).strftime("%Y%m%d")
    notif_file = f"NOTIFICATIONS-{today_str}.md"
    notif_path = paths.gados_root / "log" / "reports" / notif_file
    evidence = [
        result.ledger_rel_path,
        *( [result.escalation_rel_path] if result.escalation_rel_path else [] ),
        "log/bus/bus-events.jsonl",
        f"log/reports/{notif_file}" if notif_path.exists() else "log/reports",
    ]
    return write_beta_run(
        paths,
        meta=BetaRunMeta(
            scenario="daily-spend-guardrail",
            recommendation=rec,
            decision_summary=summary,
            required_next_action=next_action,
            pm_blockers=pm_blockers,
            top_findings=[
                {
                    "severity": sev,
                    "tool": "economics",
                    "title": f"Threshold={result.threshold or 'NONE'} spend_usd={result.spend_usd:.2f} budget_usd={result.budget_usd:.2f}",
                    "file": result.escalation_rel_path or result.ledger_rel_path,
                    "line": "",
                }
            ],
            evidence_paths=[p for p in evidence if p],
            checks=checks,
            correlation_id=result.correlation_id,
        ),
    )

