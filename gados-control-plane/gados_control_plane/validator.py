from __future__ import annotations

import re
from dataclasses import dataclass

from .artifacts import iter_story_specs, parse_story_status
from .paths import ProjectPaths


STORY_NAME_RE = re.compile(r"^STORY-\d{3}\.md$")
CHANGE_NAME_RE = re.compile(r"^CHANGE-\d{3}-[A-Z0-9]+\.ya?ml$")


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
        "memory/VERIFICATION_POLICY.md",
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

        # If story claims VERIFIED/RELEASED, ensure evidence + peer review exist
        if status and ("VERIFIED" in status or "RELEASED" in status):
            story_id = story_path.stem  # STORY-###
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

