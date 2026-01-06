from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import yaml

from .artifacts import iter_story_specs, load_yaml, parse_story_status
from .paths import ProjectPaths


STORY_NAME_RE = re.compile(r"^STORY-\d{3}\.md$")
CHANGE_NAME_RE = re.compile(r"^CHANGE-\d{3}-[A-Z0-9]+\.ya?ml$")

_STORY_STATES = [
    "PLANNED",
    "IN_PROGRESS",
    "IMPLEMENTED",
    "QA_EVIDENCE_READY",
    "PEER_REVIEWED",
    "VERIFIED",
    "RELEASED",
    "ESCALATED",
]
_STATE_RANK = {s: i for i, s in enumerate(_STORY_STATES)}


def _status_rank(status: str | None) -> int | None:
    if not status:
        return None
    # Status line may contain one of the canonical states.
    for s in _STORY_STATES:
        if s in status:
            return _STATE_RANK[s]
    return None


def _read_yaml_file(path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _has_verification_decision(*, log_path, story_id: str) -> tuple[bool, bool]:
    """
    Returns (has_verified_decision, actor_is_delivery_governor).
    """
    data = _read_yaml_file(log_path)
    if not isinstance(data, dict):
        return (False, False)
    events = data.get("events")
    if not isinstance(events, list):
        return (False, False)
    for ev in events:
        if not isinstance(ev, dict):
            continue
        if ev.get("type") != "VERIFICATION_DECISION":
            continue
        if ev.get("decision") != "VERIFIED":
            continue
        actor_ok = ev.get("actor_role") == "DeliveryGovernor"
        return (True, bool(actor_ok))
    return (False, False)


def _has_vda_approved_change_plan(paths: ProjectPaths, story_id: str) -> bool:
    """
    Any CHANGE plan that references story_id and has approvals.vda.approved == true.
    """
    changes_dir = paths.gados_root / "plan" / "changes"
    if not changes_dir.exists():
        return False
    for p in changes_dir.iterdir():
        if not (p.is_file() and p.suffix in {".yaml", ".yml"}):
            continue
        if p.name == "README.md":
            continue
        try:
            rel = str(p.relative_to(paths.gados_root))
            doc = load_yaml(paths, rel)
        except Exception:
            continue
        if str(doc.get("story_id", "")).strip() != story_id:
            continue
        approvals = doc.get("approvals") or {}
        vda = approvals.get("vda") if isinstance(approvals, dict) else {}
        if isinstance(vda, dict) and bool(vda.get("approved")) is True:
            return True
    return False


@dataclass(frozen=True)
class ValidationMessage:
    level: str  # ERROR | WARN | INFO
    code: str
    message: str
    artifact: str | None = None


def validate(paths: ProjectPaths) -> list[ValidationMessage]:
    msgs: list[ValidationMessage] = []

    # Foundational artifacts must exist
    required = [
        "memory/FOUNDATION.md",
        "memory/DESIGN_PRINCIPLES.md",
        "memory/ARCH_RULES.md",
        "memory/COMM_PROTOCOL.md",
        "memory/ARCH_DECISION_POLICY.md",
        "memory/NOTIFICATION_POLICY.md",
        "memory/SECURITY_POLICY.md",
        "memory/VERIFICATION_POLICY.md",
        "memory/ECONOMICS_LEDGER.md",
        "memory/WORKFLOW_GATES.md",
        "strategy/ARCHITECTURE.md",
        "strategy/RUNBOOKS.md",
        "templates/EPIC.template.md",
        "templates/STORY.template.md",
        "templates/CHANGE.template.yaml",
        "templates/ADR.template.md",
    ]
    for rel in required:
        p = paths.gados_root / rel
        if not p.exists():
            msgs.append(ValidationMessage("ERROR", "MISSING_ARTIFACT", f"Missing required artifact: {rel}", rel))

    # Validate story file naming + basic fields
    for story_path in iter_story_specs(paths):
        if not STORY_NAME_RE.match(story_path.name):
            msgs.append(
                ValidationMessage(
                    "WARN",
                    "BAD_STORY_NAME",
                    "Story filename should be STORY-###.md",
                    str(story_path.relative_to(paths.gados_root)),
                )
            )

        rel = str(story_path.relative_to(paths.gados_root))
        md = story_path.read_text(encoding="utf-8")
        status = parse_story_status(md)
        if status is None:
            msgs.append(ValidationMessage("WARN", "MISSING_STATUS", "Story is missing a **Status** line.", rel))

        story_id = story_path.stem  # STORY-###
        rank = _status_rank(status)

        # If story is IMPLEMENTED or beyond, require an approved change plan.
        if rank is not None and rank >= _STATE_RANK["IMPLEMENTED"]:
            if not _has_vda_approved_change_plan(paths, story_id):
                msgs.append(
                    ValidationMessage(
                        "ERROR",
                        "MISSING_APPROVED_CHANGE_PLAN",
                        "Story is IMPLEMENTED+ but no VDA-approved change plan exists (approvals.vda.approved: true).",
                        f"plan/changes (story_id={story_id})",
                    )
                )

        # If story claims VERIFIED/RELEASED, ensure evidence + peer review exist
        if status and ("VERIFIED" in status or "RELEASED" in status):
            evidence = paths.gados_root / "verification" / f"{story_id}-evidence.md"
            review = paths.gados_root / "verification" / f"{story_id}-review.md"
            log = paths.gados_root / "log" / f"{story_id}.log.yaml"
            if not evidence.exists():
                msgs.append(
                    ValidationMessage(
                        "ERROR",
                        "MISSING_EVIDENCE",
                        "Story marked VERIFIED/RELEASED but QA evidence package is missing.",
                        str(evidence.relative_to(paths.gados_root)),
                    )
                )
            if not review.exists():
                msgs.append(
                    ValidationMessage(
                        "ERROR",
                        "MISSING_PEER_REVIEW",
                        "Story marked VERIFIED/RELEASED but peer review report is missing.",
                        str(review.relative_to(paths.gados_root)),
                    )
                )
            if not log.exists():
                msgs.append(
                    ValidationMessage(
                        "ERROR",
                        "MISSING_LOG",
                        "Story marked VERIFIED/RELEASED but story audit log is missing.",
                        str(log.relative_to(paths.gados_root)),
                    )
                )
            else:
                has_decision, actor_ok = _has_verification_decision(log_path=log, story_id=story_id)
                if not has_decision:
                    msgs.append(
                        ValidationMessage(
                            "ERROR",
                            "MISSING_VERIFICATION_DECISION",
                            "Story marked VERIFIED/RELEASED but log is missing VERIFICATION_DECISION(decision: VERIFIED).",
                            str(log.relative_to(paths.gados_root)),
                        )
                    )
                elif not actor_ok:
                    msgs.append(
                        ValidationMessage(
                            "ERROR",
                            "INVALID_VERIFICATION_ACTOR",
                            "Verification decision must be made by actor_role=DeliveryGovernor (VDA).",
                            str(log.relative_to(paths.gados_root)),
                        )
                    )

    # Basic naming checks for change plans (best-effort)
    changes_dir = paths.gados_root / "plan" / "changes"
    if changes_dir.exists():
        for p in changes_dir.iterdir():
            if not p.is_file():
                continue
            if p.name == "README.md":
                continue
            if not CHANGE_NAME_RE.match(p.name):
                msgs.append(
                    ValidationMessage(
                        "WARN",
                        "BAD_CHANGE_NAME",
                        "Change plan filename should be CHANGE-###-<suffix>.yaml",
                        str(p.relative_to(paths.gados_root)),
                    )
                )

    if not msgs:
        msgs.append(ValidationMessage("INFO", "OK", "All validations passed."))
    return msgs


def format_text_report(msgs: list[ValidationMessage]) -> str:
    lines: list[str] = []
    for m in msgs:
        where = f" [{m.artifact}]" if m.artifact else ""
        lines.append(f"{m.level}: {m.code}{where} - {m.message}")
    return "\n".join(lines) + "\n"

