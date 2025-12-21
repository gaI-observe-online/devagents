from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Force the bus to use an isolated runtime/audit directory per test run.
    monkeypatch.setenv("GADOS_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("GADOS_AUDIT_DIR", str(tmp_path / "audit"))


def test_send_and_ack_message():
    from gados_control_plane.bus import ack_message, list_inbox, send_message

    msg_id = send_message(
        from_role="CoordinationAgent",
        from_agent_id="CA-1",
        to_role="QAAgent",
        to_agent_id="QA-1",
        type="EVIDENCE_REQUESTED",
        severity="INFO",
        story_id="STORY-001",
        payload={"k": "v"},
        idempotency_key="same-key",
        correlation_id="corr-1",
    )

    inbox = list_inbox(to_role="QAAgent", to_agent_id="QA-1")
    assert any(m.message_id == msg_id for m in inbox)

    ack_message(message_id=msg_id, status="ACKED", actor_role="QAAgent", actor_id="QA-1")
    inbox2 = list_inbox(to_role="QAAgent", to_agent_id="QA-1")
    assert all(m.message_id != msg_id for m in inbox2)


def test_idempotency_returns_existing_message_id():
    from gados_control_plane.bus import send_message

    msg1 = send_message(
        from_role="CoordinationAgent",
        from_agent_id="CA-1",
        to_role="PeerReviewer",
        to_agent_id="PR-1",
        type="REVIEW_REQUESTED",
        idempotency_key="idem-123",
    )
    msg2 = send_message(
        from_role="CoordinationAgent",
        from_agent_id="CA-1",
        to_role="PeerReviewer",
        to_agent_id="PR-1",
        type="REVIEW_REQUESTED",
        idempotency_key="idem-123",
    )
    assert msg1 == msg2

