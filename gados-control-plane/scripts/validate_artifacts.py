from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path so `gados_common` imports work when this
# script is executed from its subdirectory (CI runs `python gados-control-plane/scripts/...`).
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gados_control_plane.paths import get_paths  # noqa: E402
from gados_control_plane.validator import format_text_report, validate  # noqa: E402


def main() -> int:
    paths = get_paths()
    msgs = validate(paths)
    report = format_text_report(msgs)
    sys.stdout.write(report)
    has_errors = any(m.level == "ERROR" for m in msgs)
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

