from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    repo_root: Path
    gados_root: Path
    templates_dir: Path


def get_paths() -> ProjectPaths:
    """
    Resolve key project paths from the installed location.

    Assumes this package lives at: <repo>/gados-control-plane/gados_control_plane/
    """
    repo_root = Path(__file__).resolve().parents[2]
    gados_root = repo_root / "gados-project"
    templates_dir = gados_root / "templates"
    return ProjectPaths(repo_root=repo_root, gados_root=gados_root, templates_dir=templates_dir)


def safe_resolve_under(base: Path, user_path: str) -> Path:
    """
    Resolve a user-provided relative path under base, preventing path traversal.
    """
    rel = Path(user_path)
    if rel.is_absolute():
        raise ValueError("Path must be relative.")
    resolved = (base / rel).resolve()
    base_resolved = base.resolve()
    if base_resolved not in resolved.parents and resolved != base_resolved:
        raise ValueError("Path escapes base directory.")
    return resolved

