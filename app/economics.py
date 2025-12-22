import json
import math
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Category = Literal["llm", "compute", "storage", "saas", "human", "other"]
Unit = Literal["tokens", "seconds", "bytes", "dollars", "count"]
Producer = Literal["control-plane", "agent", "ci", "validator"]

Threshold = Literal["WARN", "HIGH", "CRITICAL", "HARD_STOP"]


@dataclass(frozen=True)
class LedgerEntry:
    """
    Implements `economics.ledger.entry.v1` from `gados-project/memory/ECONOMICS_LEDGER.md`.
    """

    correlation_id: str
    run_id: str
    producer: Producer
    category: Category
    unit: Unit
    quantity: float
    unit_cost_usd: float
    labels: dict[str, Any]

    vendor: str | None = None
    model: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    notes: str | None = None

    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def cost_usd(self) -> float:
        return float(self.quantity) * float(self.unit_cost_usd)

    def to_record(self) -> dict[str, Any]:
        d = asdict(self)
        d["schema"] = "economics.ledger.entry.v1"
        d["cost_usd"] = self.cost_usd()
        # Ensure labels won't crash json.dumps at runtime and won't emit non-JSON values.
        d["labels"] = _normalize_json_value(d.get("labels", {}))
        return d


def append_ledger_entry(entry: LedgerEntry, *, path: str) -> None:
    """
    Append one ledger entry to a JSONL file (audit-friendly, append-only).
    """
    record = entry.to_record()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    # One atomic append under an exclusive lock (best-effort on non-POSIX).
    # We also flush + fsync for crash-consistency of the newly appended line.
    line = json.dumps(record, separators=(",", ":"), sort_keys=True, allow_nan=False) + "\n"
    _append_jsonl_locked(path, line)


def _append_jsonl_locked(path: str, line: str) -> None:
    """
    Append `line` to `path` with best-effort cross-process locking.

    Uses `fcntl.flock` on POSIX. Falls back to an unlocked append if unavailable.
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    fd = os.open(path, flags, 0o644)
    try:
        try:
            import fcntl  # POSIX-only

            fcntl.flock(fd, fcntl.LOCK_EX)
        except Exception:
            # Non-POSIX or locking failure: proceed without a lock (best-effort).
            pass

        os.write(fd, line.encode("utf-8"))
        os.fsync(fd)
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def _normalize_json_value(value: Any, *, _depth: int = 0) -> Any:
    """
    Coerce values into JSON-safe primitives:
    - dict/list/tuple -> recursively normalized
    - uuid -> str
    - bytes -> utf-8 (replace errors)
    - floats -> if non-finite (NaN/Inf), coerce to None
    - everything else -> str(value)
    """
    if _depth > 8:
        return str(value)

    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        return value if math.isfinite(value) else None

    if isinstance(value, uuid.UUID):
        return str(value)

    # NOTE: avoid importing datetime at module import time; keep it lightweight.
    if hasattr(value, "isoformat") and callable(getattr(value, "isoformat")):
        # datetime/date-like objects
        try:
            return str(value.isoformat())
        except Exception:
            pass

    if isinstance(value, (bytes, bytearray, memoryview)):
        try:
            return bytes(value).decode("utf-8", errors="replace")
        except Exception:
            return str(value)

    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            out[str(k)] = _normalize_json_value(v, _depth=_depth + 1)
        return out

    if isinstance(value, (list, tuple, set)):
        return [_normalize_json_value(v, _depth=_depth + 1) for v in value]

    return str(value)


def total_spend_usd(entries: list[LedgerEntry]) -> float:
    return sum(e.cost_usd() for e in entries)


def top_contributors(
    entries: list[LedgerEntry],
    *,
    by: Literal["category", "vendor"] = "category",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Aggregate cost by category or vendor.

    Returns sorted list of {"key": <value>, "cost_usd": <float>}.
    """
    buckets: dict[str, float] = {}
    for e in entries:
        key = e.category if by == "category" else (e.vendor or "unknown")
        buckets[key] = buckets.get(key, 0.0) + e.cost_usd()
    ranked = sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)
    return [{"key": k, "cost_usd": v} for k, v in ranked[: max(0, limit)]]


def evaluate_threshold(*, spend_usd: float, budget_usd: float) -> Threshold | None:
    """
    Implements defaults from `gados-project/memory/ECONOMICS_LEDGER.md`.
    """
    spend = float(spend_usd)
    budget = float(budget_usd)
    if not (math.isfinite(spend) and math.isfinite(budget)):
        return None
    if budget <= 0:
        return None
    if spend < 0:
        spend = 0.0
    ratio = spend / budget
    if ratio >= 1.10:
        return "HARD_STOP"
    if ratio >= 1.00:
        return "CRITICAL"
    if ratio >= 0.90:
        return "HIGH"
    if ratio >= 0.70:
        return "WARN"
    return None


def budget_status(*, spend_usd: float, budget_usd: float) -> dict[str, float | None]:
    """
    JSON-safe budget facts (never emits NaN/Infinity).
    """
    spend = float(spend_usd)
    budget = float(budget_usd)
    if not (math.isfinite(spend) and math.isfinite(budget)):
        return {"budget_usd": None, "spend_usd": None, "margin_usd": None, "margin_pct": None}
    if spend < 0:
        spend = 0.0
    if budget <= 0:
        return {"budget_usd": budget, "spend_usd": spend, "margin_usd": None, "margin_pct": None}

    margin = budget - spend
    margin_pct = margin / budget
    # Guard against any future numeric drift (should already be finite here).
    if not (math.isfinite(margin) and math.isfinite(margin_pct)):
        return {"budget_usd": budget, "spend_usd": spend, "margin_usd": None, "margin_pct": None}
    return {"budget_usd": budget, "spend_usd": spend, "margin_usd": margin, "margin_pct": margin_pct}


def build_budget_trigger_event(
    *,
    entries: list[LedgerEntry],
    budget_usd: float,
    scope_type: Literal["intent", "day"],
    scope_id: str,
    correlation_id: str | None = None,
) -> dict[str, Any] | None:
    """
    Returns a normalized trigger payload when a threshold is met; otherwise None.

    This is intentionally transport-agnostic; a notifier can wrap/send this.
    """
    spend = total_spend_usd(entries)
    threshold = evaluate_threshold(spend_usd=spend, budget_usd=budget_usd)
    if threshold is None:
        return None

    facts = budget_status(spend_usd=spend, budget_usd=budget_usd)
    facts["threshold"] = threshold
    return {
        "schema": "gados.economics.trigger.v1",
        "event_type": "economics.budget_threshold",
        "correlation_id": correlation_id,
        "scope": {"type": scope_type, "id": scope_id},
        "summary": f"{threshold} economics threshold reached for {scope_type} {scope_id}",
        "facts": facts,
        "top_contributors": {
            "by_category": top_contributors(entries, by="category"),
            "by_vendor": top_contributors(entries, by="vendor"),
        },
    }

