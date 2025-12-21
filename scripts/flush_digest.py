import os
import sys

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

