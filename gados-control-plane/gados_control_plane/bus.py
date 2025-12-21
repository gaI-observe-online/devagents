from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .paths import get_paths


Severity = Literal["INFO", "WARN", "ERROR", "CRITICAL"]
AckStatus = Literal["ACKED", "NACKED"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _runtime_db_path() -> Path:
    paths = get_paths()
    runtime_dir = os.getenv("GADOS_RUNTIME_DIR", "").strip()
    if runtime_dir:
        return Path(runtime_dir) / "bus.sqlite3"
    return paths.repo_root / ".gados-runtime" / "bus.sqlite3"


def _audit_log_path() -> Path:
    paths = get_paths()
    audit_dir = os.getenv("GADOS_AUDIT_DIR", "").strip()
    if audit_dir:
        return Path(audit_dir) / "bus-events.jsonl"
    return paths.gados_root / "log" / "bus" / "bus-events.jsonl"


def _ensure_dirs() -> None:
    _runtime_db_path().parent.mkdir(parents=True, exist_ok=True)
    _audit_log_path().parent.mkdir(parents=True, exist_ok=True)


def _connect() -> sqlite3.Connection:
    _ensure_dirs()
    con = sqlite3.connect(str(_runtime_db_path()))
    con.row_factory = sqlite3.Row
    return con


def _init_db() -> None:
    with _connect() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
              message_id TEXT PRIMARY KEY,
              idempotency_key TEXT NOT NULL,
              created_at TEXT NOT NULL,
              from_role TEXT NOT NULL,
              from_agent_id TEXT NOT NULL,
              to_role TEXT NOT NULL,
              to_agent_id TEXT NOT NULL,
              type TEXT NOT NULL,
              severity TEXT NOT NULL,
              correlation_id TEXT NOT NULL,
              story_id TEXT,
              epic_id TEXT,
              artifact_refs_json TEXT,
              payload_json TEXT NOT NULL,
              status TEXT NOT NULL,                -- PENDING | ACKED | DEAD
              attempts INTEGER NOT NULL DEFAULT 0,
              last_error TEXT
            );
            """
        )
        con.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_idempotency
            ON messages(from_role, from_agent_id, idempotency_key);
            """
        )


def _append_audit(event: dict[str, Any]) -> None:
    _ensure_dirs()
    line = json.dumps(event, separators=(",", ":"), ensure_ascii=False)
    with _audit_log_path().open("a", encoding="utf-8") as f:
        f.write(line + "\n")


@dataclass(frozen=True)
class Message:
    message_id: str
    idempotency_key: str
    created_at: str
    from_role: str
    from_agent_id: str
    to_role: str
    to_agent_id: str
    type: str
    severity: Severity
    correlation_id: str
    story_id: str | None
    epic_id: str | None
    artifact_refs: list[str]
    payload: dict[str, Any]
    status: str
    attempts: int
    last_error: str | None


def send_message(
    *,
    from_role: str,
    from_agent_id: str,
    to_role: str,
    to_agent_id: str,
    type: str,
    severity: Severity = "INFO",
    correlation_id: str | None = None,
    idempotency_key: str | None = None,
    story_id: str | None = None,
    epic_id: str | None = None,
    artifact_refs: list[str] | None = None,
    payload: dict[str, Any] | None = None,
) -> str:
    """
    Enqueue a message with at-least-once delivery semantics.
    If the (from_role, from_agent_id, idempotency_key) already exists, returns the existing message_id.
    """
    _init_db()
    now = _utc_now_iso()
    msg_id = str(uuid.uuid4())
    corr = correlation_id or str(uuid.uuid4())
    idem = idempotency_key or str(uuid.uuid4())
    refs = artifact_refs or []
    body = payload or {}

    with _connect() as con:
        try:
            con.execute(
                """
                INSERT INTO messages (
                  message_id, idempotency_key, created_at,
                  from_role, from_agent_id, to_role, to_agent_id,
                  type, severity, correlation_id, story_id, epic_id,
                  artifact_refs_json, payload_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
                """,
                (
                    msg_id,
                    idem,
                    now,
                    from_role,
                    from_agent_id,
                    to_role,
                    to_agent_id,
                    type,
                    severity,
                    corr,
                    story_id,
                    epic_id,
                    json.dumps(refs),
                    json.dumps(body),
                ),
            )
        except sqlite3.IntegrityError:
            row = con.execute(
                """
                SELECT message_id FROM messages
                WHERE from_role=? AND from_agent_id=? AND idempotency_key=?
                """,
                (from_role, from_agent_id, idem),
            ).fetchone()
            if row:
                return str(row["message_id"])
            raise

    _append_audit(
        {
            "schema": "gados.bus.event.v1",
            "event_type": "MESSAGE_SENT",
            "at": now,
            "message": {
                "schema": "gados.bus.message.v1",
                "message_id": msg_id,
                "idempotency_key": idem,
                "created_at": now,
                "from": {"role": from_role, "agent_id": from_agent_id},
                "to": {"role": to_role, "agent_id": to_agent_id},
                "type": type,
                "severity": severity,
                "correlation_id": corr,
                "story_id": story_id,
                "epic_id": epic_id,
                "artifact_refs": refs,
                "payload": body,
            },
        }
    )
    return msg_id


def list_inbox(*, to_role: str, to_agent_id: str, limit: int = 50) -> list[Message]:
    _init_db()
    with _connect() as con:
        rows = con.execute(
            """
            SELECT * FROM messages
            WHERE status='PENDING'
              AND to_role=?
              AND (to_agent_id=? OR to_agent_id='*')
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (to_role, to_agent_id, limit),
        ).fetchall()

    out: list[Message] = []
    for r in rows:
        out.append(
            Message(
                message_id=str(r["message_id"]),
                idempotency_key=str(r["idempotency_key"]),
                created_at=str(r["created_at"]),
                from_role=str(r["from_role"]),
                from_agent_id=str(r["from_agent_id"]),
                to_role=str(r["to_role"]),
                to_agent_id=str(r["to_agent_id"]),
                type=str(r["type"]),
                severity=str(r["severity"]),  # type: ignore[assignment]
                correlation_id=str(r["correlation_id"]),
                story_id=r["story_id"],
                epic_id=r["epic_id"],
                artifact_refs=list(json.loads(r["artifact_refs_json"] or "[]")),
                payload=dict(json.loads(r["payload_json"] or "{}")),
                status=str(r["status"]),
                attempts=int(r["attempts"]),
                last_error=r["last_error"],
            )
        )
    return out


def ack_message(*, message_id: str, status: AckStatus, actor_role: str, actor_id: str, notes: str = "") -> None:
    _init_db()
    now = _utc_now_iso()
    with _connect() as con:
        row = con.execute("SELECT * FROM messages WHERE message_id=?", (message_id,)).fetchone()
        if not row:
            raise KeyError(message_id)
        new_status = "ACKED" if status == "ACKED" else "PENDING"
        attempts = int(row["attempts"])
        if status == "NACKED":
            attempts += 1
        con.execute(
            "UPDATE messages SET status=?, attempts=?, last_error=? WHERE message_id=?",
            (new_status, attempts, notes or row["last_error"], message_id),
        )

    _append_audit(
        {
            "schema": "gados.bus.event.v1",
            "event_type": status,
            "at": now,
            "message_id": message_id,
            "actor": {"role": actor_role, "agent_id": actor_id},
            "notes": notes,
        }
    )

