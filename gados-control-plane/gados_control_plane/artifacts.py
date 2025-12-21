from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

from .paths import ProjectPaths, safe_resolve_under


@dataclass(frozen=True)
class ArtifactInfo:
    rel_path: str
    kind: str  # directory | file


STATUS_RE = re.compile(r"^\*\*Status\*\*:\s*(.+?)\s*$", re.IGNORECASE)


def list_artifacts(paths: ProjectPaths, rel_dir: str = "") -> list[ArtifactInfo]:
    base = paths.gados_root
    target = base if rel_dir == "" else safe_resolve_under(base, rel_dir)
    if not target.exists():
        return []
    if target.is_file():
        return [ArtifactInfo(rel_path=rel_dir, kind="file")]

    items: list[ArtifactInfo] = []
    for p in sorted(target.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
        if p.name.startswith("."):
            continue
        rel = str(p.relative_to(base))
        items.append(ArtifactInfo(rel_path=rel, kind="file" if p.is_file() else "directory"))
    return items


def read_text(paths: ProjectPaths, rel_path: str) -> str:
    p = safe_resolve_under(paths.gados_root, rel_path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(rel_path)
    return p.read_text(encoding="utf-8")


def write_text(paths: ProjectPaths, rel_path: str, content: str) -> None:
    p = safe_resolve_under(paths.gados_root, rel_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def append_text(paths: ProjectPaths, rel_path: str, content: str) -> None:
    p = safe_resolve_under(paths.gados_root, rel_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(content, encoding="utf-8")
        return
    with p.open("a", encoding="utf-8") as f:
        f.write(content)


def load_yaml(paths: ProjectPaths, rel_path: str) -> dict:
    raw = read_text(paths, rel_path)
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping.")
    return data


def dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, sort_keys=False)


def iter_story_specs(paths: ProjectPaths) -> Iterable[Path]:
    story_dir = paths.gados_root / "plan" / "stories"
    if not story_dir.exists():
        return []
    return (p for p in story_dir.iterdir() if p.is_file() and p.name.startswith("STORY-") and p.suffix == ".md")


def parse_story_status(markdown: str) -> str | None:
    for line in markdown.splitlines():
        m = STATUS_RE.match(line.strip())
        if m:
            return m.group(1).strip()
    return None

