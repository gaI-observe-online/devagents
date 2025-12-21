import json
from pathlib import Path

from app.economics import LedgerEntry, append_ledger_entry


def test_append_ledger_entry_writes_jsonl(tmp_path: Path):
    ledger_path = tmp_path / "ledger.jsonl"
    entry = LedgerEntry(
        correlation_id="intent_123",
        run_id="ci_456",
        producer="ci",
        category="compute",
        unit="seconds",
        quantity=120.0,
        unit_cost_usd=0.0005,
        labels={"service": "gados-control-plane", "env": "test"},
        vendor="github-actions",
    )

    append_ledger_entry(entry, path=str(ledger_path))

    lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj["schema"] == "economics.ledger.entry.v1"
    assert obj["correlation_id"] == "intent_123"
    assert obj["run_id"] == "ci_456"
    assert obj["producer"] == "ci"
    assert obj["category"] == "compute"
    assert obj["unit"] == "seconds"
    assert obj["quantity"] == 120.0
    assert obj["unit_cost_usd"] == 0.0005
    assert obj["cost_usd"] == 120.0 * 0.0005
    assert obj["labels"]["service"] == "gados-control-plane"

