from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml
from opentelemetry import trace

from app.notifications import Notification, dispatch_notification

from .bus import send_message
from .paths import ProjectPaths


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class Drift:
    key: str
    expected: str
    actual: str
    severity: str


@dataclass(frozen=True)
class PolicyDriftResult:
    correlation_id: str
    baseline_rel_path: str
    drift_count: int
    max_severity: str
    report_rel_path: str | None
    bus_message_id: str | None
    notification_queued_path: str | None


_SEV_RANK = {"LOW": 10, "MEDIUM": 20, "HIGH": 30, "CRITICAL": 40}


def _rank(sev: str) -> int:
    return _SEV_RANK.get(sev.upper(), 10)


def _bus_severity(max_sev: str) -> str:
    s = max_sev.upper()
    if s in {"HIGH", "CRITICAL"}:
        return "ERROR"
    if s == "MEDIUM":
        return "WARN"
    return "INFO"


def _load_baseline(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ValueError("baseline YAML must be a mapping")
    return data


def _normalize_expected(entry: dict) -> tuple[str, list[str]]:
    if "expected_one_of" in entry:
        vals = entry.get("expected_one_of") or []
        if not isinstance(vals, list):
            vals = [str(vals)]
        return "one_of", [str(v) for v in vals]
    if "expected" in entry:
        return "exact", [str(entry.get("expected"))]
    return "unknown", []


def _coerce_actual(t: str, raw: str | None) -> str:
    if raw is None:
        raw = ""
    if t == "int":
        try:
            return str(int(raw))
        except Exception:
            return raw
    if t == "float":
        try:
            v = float(raw)
            # stable string representation
            return str(int(v)) if v.is_integer() else str(v)
        except Exception:
            return raw
    return str(raw)


def _expected_matches(t: str, kind: str, expected: list[str], actual: str) -> bool:
    if kind == "one_of":
        return actual in expected
    if kind == "exact":
        # Compare in coerced form for numeric types.
        if t in {"int", "float"}:
            return _coerce_actual(t, expected[0] if expected else "") == actual
        return (expected[0] if expected else "") == actual
    return True


def run_policy_drift_watchdog(
    *,
    paths: ProjectPaths,
    baseline_rel_path: str = "memory/BETA_POLICY_BASELINE.yaml",
    correlation_id: str | None = None,
) -> PolicyDriftResult:
    """
    Beta scenario: compare runtime config/env against an approved baseline.

    On drift:
    - write an auditable drift report artifact under gados-project/log/reports/
    - emit a bus event (Inbox UI) and queue a notification (digest)
    """
    tracer = trace.get_tracer("gados-control-plane")
    corr = correlation_id or str(uuid.uuid4())

    baseline_path = paths.gados_root / baseline_rel_path
    baseline = _load_baseline(baseline_path)
    policies = baseline.get("policies") or {}
    if not isinstance(policies, dict):
        raise ValueError("baseline 'policies' must be a mapping")

    drifts: list[Drift] = []
    for key, spec in policies.items():
        if not isinstance(spec, dict):
            continue
        t = str(spec.get("type", "str")).strip().lower()
        sev = str(spec.get("severity", "LOW")).strip().upper()
        kind, expected_vals = _normalize_expected(spec)
        actual = _coerce_actual(t, os.getenv(str(key)))
        if not _expected_matches(t, kind, expected_vals, actual):
            expected_str = (
                f"one_of={expected_vals}" if kind == "one_of" else (expected_vals[0] if expected_vals else "")
            )
            drifts.append(Drift(key=str(key), expected=expected_str, actual=actual, severity=sev))

    max_sev = "LOW"
    for d in drifts:
        if _rank(d.severity) > _rank(max_sev):
            max_sev = d.severity

    report_rel: str | None = None
    msg_id: str | None = None
    queued_path: str | None = None

    with tracer.start_as_current_span("beta.policy_drift_watchdog") as span:
        span.set_attribute("gados.correlation_id", corr)
        span.set_attribute("gados.drift_count", len(drifts))
        span.set_attribute("gados.max_severity", max_sev)
        span.set_attribute("gados.baseline", baseline_rel_path)

        if drifts:
            reports_dir = paths.gados_root / "log" / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            stamp = _utc_now_iso().split("+", 1)[0].replace(":", "").replace("-", "").replace("T", "-")
            report_path = reports_dir / f"POLICY-DRIFT-{stamp}.md"
            report_rel = str(report_path.relative_to(paths.gados_root))

            lines: list[str] = []
            lines.append("# Policy Drift Report")
            lines.append("")
            lines.append(f"**Generated (UTC)**: {_utc_now_iso()}")
            lines.append(f"**Baseline**: `{baseline_rel_path}`")
            lines.append(f"**Correlation ID**: `{corr}`")
            lines.append(f"**Drift count**: {len(drifts)}")
            lines.append(f"**Max severity**: **{max_sev}**")
            lines.append("")
            lines.append("## Drifts")
            for d in sorted(drifts, key=lambda x: (-_rank(x.severity), x.key)):
                lines.append(f"- **{d.severity}** `{d.key}` expected `{d.expected}` got `{d.actual}`")
            lines.append("")
            report_path.write_text("\n".join(lines), encoding="utf-8")

            payload = {
                "schema": "gados.policy.drift.v1",
                "event_type": "policy.drift_detected",
                "at": _utc_now_iso(),
                "correlation_id": corr,
                "baseline": baseline_rel_path,
                "max_severity": max_sev,
                "drifts": [d.__dict__ for d in drifts],
                "report_rel_path": report_rel,
            }

            # Bus message (Inbox UI)
            msg_id = send_message(
                from_role="PolicyWatchdog",
                from_agent_id="POL-1",
                to_role="CoordinationAgent",
                to_agent_id="CA-1",
                type="policy.drift_detected",
                severity=_bus_severity(max_sev),  # type: ignore[arg-type]
                correlation_id=corr,
                artifact_refs=[report_rel],
                payload=payload,
            )

            # Notification queue (digest)
            nr = dispatch_notification(
                Notification(
                    type="policy.drift_detected",
                    severity=_bus_severity(max_sev),  # type: ignore[arg-type]
                    correlation_id=corr,
                    artifact_refs=[report_rel],
                    payload=payload,
                )
            )
            queued_path = str(nr.get("queued_path")) if nr else None

    return PolicyDriftResult(
        correlation_id=corr,
        baseline_rel_path=baseline_rel_path,
        drift_count=len(drifts),
        max_severity=max_sev,
        report_rel_path=report_rel,
        bus_message_id=msg_id,
        notification_queued_path=queued_path,
    )

