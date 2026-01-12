import json
from pathlib import Path

from app.economics import (
    LedgerEntry,
    append_ledger_entry,
    build_budget_trigger_event,
    evaluate_threshold,
    top_contributors,
    total_spend_usd,
)


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


def test_append_ledger_entry_coerces_non_json_labels(tmp_path: Path):
    ledger_path = tmp_path / "ledger.jsonl"
    entry = LedgerEntry(
        correlation_id="intent_123",
        run_id="ci_456",
        producer="ci",
        category="compute",
        unit="seconds",
        quantity=1.0,
        unit_cost_usd=1.0,
        labels={"bytes": b"\xff", "uuid": __import__("uuid").uuid4(), "nan": float("nan")},
    )
    append_ledger_entry(entry, path=str(ledger_path))
    obj = json.loads(ledger_path.read_text(encoding="utf-8").strip())
    assert isinstance(obj["labels"]["bytes"], str)
    assert isinstance(obj["labels"]["uuid"], str)
    assert obj["labels"]["nan"] is None


def test_threshold_evaluation_defaults():
    assert evaluate_threshold(spend_usd=0.0, budget_usd=10.0) is None
    assert evaluate_threshold(spend_usd=6.99, budget_usd=10.0) is None
    assert evaluate_threshold(spend_usd=7.00, budget_usd=10.0) == "WARN"
    assert evaluate_threshold(spend_usd=9.00, budget_usd=10.0) == "HIGH"
    assert evaluate_threshold(spend_usd=10.00, budget_usd=10.0) == "CRITICAL"
    assert evaluate_threshold(spend_usd=11.00, budget_usd=10.0) == "HARD_STOP"


def test_budget_trigger_payload_includes_top_contributors():
    entries = [
        LedgerEntry(
            correlation_id="intent_123",
            run_id="ci_1",
            producer="ci",
            category="llm",
            unit="tokens",
            quantity=1000,
            unit_cost_usd=0.001,
            labels={"service": "gados-control-plane", "env": "test"},
            vendor="openai",
        ),
        LedgerEntry(
            correlation_id="intent_123",
            run_id="ci_2",
            producer="ci",
            category="compute",
            unit="seconds",
            quantity=200,
            unit_cost_usd=0.001,
            labels={"service": "gados-control-plane", "env": "test"},
            vendor="github-actions",
        ),
    ]
    assert total_spend_usd(entries) == (1000 * 0.001) + (200 * 0.001)

    payload = build_budget_trigger_event(
        entries=entries,
        budget_usd=1.0,
        scope_type="intent",
        scope_id="intent_123",
        correlation_id="intent_123",
    )
    assert payload is not None
    assert payload["schema"] == "gados.economics.trigger.v1"
    assert payload["facts"]["threshold"] in {"CRITICAL", "HARD_STOP"}
    assert payload["top_contributors"]["by_category"][0]["key"] == "llm"
    assert payload["top_contributors"]["by_vendor"][0]["key"] == "openai"


def test_top_contributors_vendor_unknown():
    entries = [
        LedgerEntry(
            correlation_id="intent_123",
            run_id="ci_1",
            producer="ci",
            category="other",
            unit="count",
            quantity=1,
            unit_cost_usd=2.0,
            labels={"service": "gados-control-plane", "env": "test"},
        )
    ]
    ranked = top_contributors(entries, by="vendor")
    assert ranked[0]["key"] == "unknown"

