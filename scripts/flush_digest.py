"""Flush queued daily digest notifications.

This script is designed to be run from the repo root or via `make notify-digest-flush`.
"""

# ruff: noqa: E402

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from app.notifications import flush_daily_digest


def main() -> int:
    webhook_url = os.getenv("GADOS_WEBHOOK_URL", "").strip()
    store_path = os.getenv("GADOS_DIGEST_STORE_PATH", "/tmp/gados_digest.jsonl")
    secret = os.getenv("GADOS_WEBHOOK_SECRET")

    if not webhook_url:
        print("GADOS_WEBHOOK_URL is required to flush digest", file=sys.stderr)
        return 2

    shipped = flush_daily_digest(webhook_url=webhook_url, store_path=store_path, secret=secret)
    print(f"shipped_digest_events={shipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

