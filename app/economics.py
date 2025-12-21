import json
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
        return d


def append_ledger_entry(entry: LedgerEntry, *, path: str) -> None:
    """
    Append one ledger entry to a JSONL file (audit-friendly, append-only).
    """
    record = entry.to_record()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":"), sort_keys=True))
        f.write("\n")


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
    if budget_usd <= 0:
        return None
    ratio = spend_usd / budget_usd
    if ratio >= 1.10:
        return "HARD_STOP"
    if ratio >= 1.00:
        return "CRITICAL"
    if ratio >= 0.90:
        return "HIGH"
    if ratio >= 0.70:
        return "WARN"
    return None


def budget_status(*, spend_usd: float, budget_usd: float) -> dict[str, float]:
    if budget_usd <= 0:
        return {"budget_usd": float(budget_usd), "spend_usd": float(spend_usd), "margin_usd": float("nan")}
    return {
        "budget_usd": float(budget_usd),
        "spend_usd": float(spend_usd),
        "margin_usd": float(budget_usd) - float(spend_usd),
        "margin_pct": (float(budget_usd) - float(spend_usd)) / float(budget_usd),
    }


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

