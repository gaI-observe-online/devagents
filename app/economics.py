import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Category = Literal["llm", "compute", "storage", "saas", "human", "other"]
Unit = Literal["tokens", "seconds", "bytes", "dollars", "count"]
Producer = Literal["control-plane", "agent", "ci", "validator"]


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

