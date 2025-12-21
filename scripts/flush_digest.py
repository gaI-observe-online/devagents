from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import sys


def main() -> int:
    # Ensure repo root is importable when executed from elsewhere.
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

    from app.notifications import flush_daily_digest  # local import avoids ruff E402

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    output = Path("gados-project") / "log" / "reports" / f"NOTIFICATIONS-{stamp}.md"
    result = flush_daily_digest(output_path=output, truncate=True)
    print(f"flushed={result['flushed']} truncated={result['truncated']} output={result['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

