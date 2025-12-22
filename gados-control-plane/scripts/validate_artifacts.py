from __future__ import annotations

import sys

from gados_control_plane.paths import get_paths
from gados_control_plane.validator import format_text_report, validate


def main() -> int:
    paths = get_paths()
    msgs = validate(paths)
    report = format_text_report(msgs)
    sys.stdout.write(report)
    has_errors = any(m.level == "ERROR" for m in msgs)
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

