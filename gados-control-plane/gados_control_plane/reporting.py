from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .artifacts import iter_story_specs, parse_story_status
from .paths import ProjectPaths
from .validator import ValidationMessage, validate


def _parse_dt(value: str) -> datetime | None:
    # Supports "2025-01-01T00:00:00+00:00" (isoformat) and "Z" suffix.
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _read_yaml_file(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None


@dataclass(frozen=True)
class Metrics:
    epic_count: int
    story_count: int
    stories_by_status: dict[str, int]
    verified_story_count: int
    avg_time_to_verified_hours: float | None
    validation_errors: int
    validation_warnings: int


def compute_metrics(paths: ProjectPaths) -> Metrics:
    # Epics
    epic_dir = paths.gados_root / "strategy"
    epic_count = 0
    if epic_dir.exists():
        epic_count = len([p for p in epic_dir.iterdir() if p.is_file() and p.name.startswith("EPIC-") and p.suffix == ".md"])

    # Stories and statuses
    stories_by_status: dict[str, int] = {}
    story_count = 0
    verified_story_ids: list[str] = []
    for story_path in iter_story_specs(paths):
        story_count += 1
        md = story_path.read_text(encoding="utf-8")
        status = parse_story_status(md) or "UNKNOWN"
        stories_by_status[status] = stories_by_status.get(status, 0) + 1
        if "VERIFIED" in status or "RELEASED" in status:
            verified_story_ids.append(story_path.stem)

    # Time to verified (best-effort, from story log events)
    durations_hours: list[float] = []
    for story_id in verified_story_ids:
        log_path = paths.gados_root / "log" / f"{story_id}.log.yaml"
        if not log_path.exists():
            continue
        data = _read_yaml_file(log_path)
        if not isinstance(data, dict):
            continue
        events = data.get("events")
        if not isinstance(events, list):
            continue

        t_in_progress: datetime | None = None
        t_verified: datetime | None = None
        for ev in events:
            if not isinstance(ev, dict):
                continue
            at = ev.get("at")
            if not isinstance(at, str):
                continue
            dt = _parse_dt(at)
            if dt is None:
                continue

            if ev.get("type") == "STATUS_CHANGED" and ev.get("to") == "IN_PROGRESS":
                if t_in_progress is None or dt < t_in_progress:
                    t_in_progress = dt
            if ev.get("type") == "VERIFICATION_DECISION" and ev.get("decision") == "VERIFIED":
                if t_verified is None or dt < t_verified:
                    t_verified = dt

        if t_in_progress and t_verified and t_verified >= t_in_progress:
            durations_hours.append((t_verified - t_in_progress).total_seconds() / 3600.0)

    avg_time = None
    if durations_hours:
        avg_time = sum(durations_hours) / len(durations_hours)

    msgs = validate(paths)
    validation_errors = sum(1 for m in msgs if m.level == "ERROR")
    validation_warnings = sum(1 for m in msgs if m.level == "WARN")

    return Metrics(
        epic_count=epic_count,
        story_count=story_count,
        stories_by_status=dict(sorted(stories_by_status.items(), key=lambda kv: (-kv[1], kv[0]))),
        verified_story_count=len(verified_story_ids),
        avg_time_to_verified_hours=avg_time,
        validation_errors=validation_errors,
        validation_warnings=validation_warnings,
    )


def render_daily_report_md(
    *,
    now_utc_iso: str,
    metrics: Metrics,
    validations: list[ValidationMessage],
) -> str:
    lines: list[str] = []
    lines.append(f"# GADOS Daily Governance Digest")
    lines.append("")
    lines.append(f"**Generated (UTC)**: {now_utc_iso}")
    lines.append("")

    lines.append("## Snapshot")
    lines.append(f"- **Epics**: {metrics.epic_count}")
    lines.append(f"- **Stories**: {metrics.story_count}")
    lines.append(f"- **Verified/Released stories**: {metrics.verified_story_count}")
    if metrics.avg_time_to_verified_hours is None:
        lines.append("- **Avg time to verified**: n/a (insufficient log data)")
    else:
        lines.append(f"- **Avg time to verified**: {metrics.avg_time_to_verified_hours:.2f} hours")
    lines.append(f"- **Governance validation**: {metrics.validation_errors} error(s), {metrics.validation_warnings} warning(s)")
    lines.append("")

    lines.append("## Status distribution")
    if metrics.stories_by_status:
        for status, count in metrics.stories_by_status.items():
            lines.append(f"- `{status}`: **{count}**")
    else:
        lines.append("- (no stories found)")
    lines.append("")

    lines.append("## Governance findings (validator)")
    if validations:
        for v in validations:
            where = f" [{v.artifact}]" if v.artifact else ""
            lines.append(f"- **{v.level}** `{v.code}`{where}: {v.message}")
    else:
        lines.append("- (no findings)")
    lines.append("")

    lines.append("## Notes")
    lines.append("- This report is derived from versioned artifacts under `/gados-project/`.")
    lines.append("- Certification of `VERIFIED` remains VDA authority and must be evidence-backed.")
    lines.append("")
    return "\n".join(lines)

