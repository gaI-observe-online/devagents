from __future__ import annotations

import os
from pathlib import Path


def append_text_locked(path: str | Path, text: str, *, encoding: str = "utf-8") -> None:
    """
    Append text to a file with best-effort cross-process locking + fsync.

    - Uses `fcntl.flock` on POSIX.
    - Falls back to an unlocked append if locking isn't available.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    fd = os.open(str(p), flags, 0o644)
    try:
        try:
            import fcntl  # POSIX-only

            fcntl.flock(fd, fcntl.LOCK_EX)
        except Exception:
            # Non-POSIX or locking failure: proceed without a lock (best-effort).
            pass

        os.write(fd, text.encode(encoding))
        os.fsync(fd)
    finally:
        try:
            os.close(fd)
        except OSError:
            pass

