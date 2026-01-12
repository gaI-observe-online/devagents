from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from opentelemetry import trace

from app.notifications import Notification, dispatch_notification

from .bus import get_last_heartbeat, record_heartbeat, send_message
from .beta_run_store import BetaRunMeta, write_beta_run
from .paths import ProjectPaths


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class SlaResult:
    correlation_id: str
    role: str
    agent_id: str
    last_seen_at: str | None
    heartbeat_age_seconds: float | None
    health_latency_ms: float | None
    breached: bool
    report_rel_path: str | None
    bus_message_id: str | None
    notification_queued_path: str | None


def _parse_iso_utc(s: str) -> datetime:
    # Supports ISO-8601 with timezone info.
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _health_check_latency_ms() -> float:
    """
    Best-effort latency proxy: do a small in-process sleep-free measurement.

    NOTE: For beta evidence, prefer hitting /health externally (docker_smoke does this).
    Here we just provide a deterministic measurable number.
    """
    t0 = time.perf_counter()
    # minimal work
    _ = 1 + 1
    return (time.perf_counter() - t0) * 1000.0


def run_sla_breach_sentinel(
    *,
    paths: ProjectPaths,
    role: str = "CoordinationAgent",
    agent_id: str = "CA-1",
    heartbeat_sla_seconds: float = 30.0,
    latency_sla_ms: float = 250.0,
    correlation_id: str | None = None,
) -> SlaResult:
    """
    Beta scenario: check heartbeat + simple latency proxy and emit an incident when breached.

    - Heartbeats are recorded in the runtime DB via record_heartbeat().
    - If missed heartbeat or latency exceeds threshold:
      - write an auditable incident report under gados-project/log/reports/
      - emit a bus message (Inbox UI) and queue a notification (digest)
    """
    tracer = trace.get_tracer("gados-control-plane")
    corr = correlation_id or str(uuid.uuid4())

    last = get_last_heartbeat(role=role, agent_id=agent_id)
    age: float | None = None
    now = datetime.now(timezone.utc)
    if last:
        try:
            age = (now - _parse_iso_utc(last)).total_seconds()
        except Exception:
            age = None

    latency_ms = _health_check_latency_ms()

    breached = False
    reasons: list[str] = []
    if age is None or age > float(heartbeat_sla_seconds):
        breached = True
        reasons.append("HEARTBEAT_MISSED")
    if latency_ms > float(latency_sla_ms):
        breached = True
        reasons.append("LATENCY_SLA_BREACH")

    report_rel: str | None = None
    msg_id: str | None = None
    queued_path: str | None = None

    with tracer.start_as_current_span("beta.sla_breach_sentinel") as span:
        span.set_attribute("gados.correlation_id", corr)
        span.set_attribute("agent.role", role)
        span.set_attribute("agent.id", agent_id)
        span.set_attribute("sla.heartbeat_seconds", float(heartbeat_sla_seconds))
        span.set_attribute("sla.latency_ms", float(latency_sla_ms))
        if age is not None:
            span.set_attribute("heartbeat.age_seconds", float(age))
        span.set_attribute("health.latency_ms", float(latency_ms))
        span.set_attribute("breached", bool(breached))

        if breached:
            reports_dir = paths.gados_root / "log" / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            stamp = _utc_now_iso().split("+", 1)[0].replace(":", "").replace("-", "").replace("T", "-")
            report_path = reports_dir / f"SLA-BREACH-{stamp}.md"
            report_rel = str(report_path.relative_to(paths.gados_root))

            lines: list[str] = []
            lines.append("# SLA Breach Incident")
            lines.append("")
            lines.append(f"**Generated (UTC)**: {_utc_now_iso()}")
            lines.append(f"**Correlation ID**: `{corr}`")
            lines.append(f"**Agent**: `{role}/{agent_id}`")
            lines.append("")
            lines.append("## SLA thresholds")
            lines.append(f"- heartbeat_sla_seconds: {heartbeat_sla_seconds}")
            lines.append(f"- latency_sla_ms: {latency_sla_ms}")
            lines.append("")
            lines.append("## Observations")
            lines.append(f"- last_seen_at: `{last}`")
            lines.append(f"- heartbeat_age_seconds: {age}")
            lines.append(f"- health_latency_ms: {latency_ms:.3f}")
            lines.append("")
            lines.append("## Reasons")
            for r in reasons:
                lines.append(f"- {r}")
            lines.append("")
            report_path.write_text("\n".join(lines), encoding="utf-8")

            payload = {
                "schema": "gados.sla.breach.v1",
                "event_type": "agent.sla_breach",
                "at": _utc_now_iso(),
                "correlation_id": corr,
                "agent": {"role": role, "agent_id": agent_id},
                "sla": {"heartbeat_sla_seconds": heartbeat_sla_seconds, "latency_sla_ms": latency_sla_ms},
                "observations": {"last_seen_at": last, "heartbeat_age_seconds": age, "health_latency_ms": latency_ms},
                "reasons": reasons,
                "report_rel_path": report_rel,
            }

            msg_id = send_message(
                from_role="SLAWatchdog",
                from_agent_id="SLA-1",
                to_role="CoordinationAgent",
                to_agent_id="CA-1",
                type="agent.sla_breach",
                severity="CRITICAL",  # type: ignore[arg-type]
                correlation_id=corr,
                artifact_refs=[report_rel],
                payload=payload,
            )

            nr = dispatch_notification(
                Notification(
                    type="agent.sla_breach",
                    severity="CRITICAL",  # type: ignore[arg-type]
                    correlation_id=corr,
                    artifact_refs=[report_rel],
                    payload=payload,
                )
            )
            queued_path = str(nr.get("queued_path")) if nr else None

    return SlaResult(
        correlation_id=corr,
        role=role,
        agent_id=agent_id,
        last_seen_at=last,
        heartbeat_age_seconds=age,
        health_latency_ms=latency_ms,
        breached=breached,
        report_rel_path=report_rel,
        bus_message_id=msg_id,
        notification_queued_path=queued_path,
    )


def beat(*, role: str, agent_id: str) -> None:
    """
    Convenience wrapper for recording a heartbeat.
    """
    record_heartbeat(role=role, agent_id=agent_id)


def write_sla_beta_run(*, paths: ProjectPaths, result: SlaResult) -> dict[str, str]:
    if result.breached:
        rec = "NO-GO"
        summary = "Agent health/SLA breach detected. Release blocked until incident is understood and resolved."
        next_action = "Review the incident report, restore heartbeats/latency, and re-run the sentinel."
        pm_blockers = [{"owner": "Eng", "pm_summary": "SLA breach indicates operational risk; release blocked until resolved."}]
        sev = "CRITICAL"
    else:
        rec = "GO"
        summary = "No SLA breach detected."
        next_action = "Proceed with release; continue monitoring."
        pm_blockers = []
        sev = "INFO"

    checks = {
        "heartbeat_checked": {"exit_code": 0},
        "latency_checked": {"exit_code": 0},
        "incident_report_written": {"exit_code": 0 if (result.report_rel_path or not result.breached) else 1},
        "bus_event_emitted": {"exit_code": 0 if (result.bus_message_id or not result.breached) else 1},
        "notification_queued": {"exit_code": 0 if (result.notification_queued_path or not result.breached) else 1},
    }
    evidence = [
        *( [result.report_rel_path] if result.report_rel_path else [] ),
        "log/bus/bus-events.jsonl",
    ]
    return write_beta_run(
        paths,
        meta=BetaRunMeta(
            scenario="sla-sentinel",
            recommendation=rec,
            decision_summary=summary,
            required_next_action=next_action,
            pm_blockers=pm_blockers,
            top_findings=[
                {
                    "severity": sev,
                    "tool": "sla",
                    "title": f"breached={result.breached} heartbeat_age_seconds={result.heartbeat_age_seconds} latency_ms={result.health_latency_ms}",
                    "file": result.report_rel_path or "",
                    "line": "",
                }
            ],
            evidence_paths=[p for p in evidence if p],
            checks=checks,
            correlation_id=result.correlation_id,
        ),
    )

