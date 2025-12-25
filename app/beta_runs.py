import json
import os
import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


RunStatus = Literal["running", "succeeded", "failed", "cancelled"]


class BetaRun(BaseModel):
    schema: Literal["gados.beta.run.v1"] = "gados.beta.run.v1"

    run_id: str
    project_id: str
    project_name: str | None = None

    environment: str = "beta"  # "beta" | "test" (caller-defined)
    status: RunStatus = "running"

    correlation_id: str | None = None
    triggered_by: str | None = None
    finished_by: str | None = None

    labels: dict[str, Any] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)

    started_at: float
    finished_at: float | None = None
    updated_at: float


class BetaRunStartRequest(BaseModel):
    project_id: str = Field(min_length=1)
    project_name: str | None = None
    environment: str = "beta"
    correlation_id: str | None = None
    triggered_by: str | None = None
    labels: dict[str, Any] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)


class BetaRunCompleteRequest(BaseModel):
    status: Literal["succeeded", "failed", "cancelled"]
    finished_by: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


def _store_path() -> str:
    return os.getenv("GADOS_BETA_RUN_STORE_PATH", "/tmp/gados_beta_runs.jsonl")


def _append_jsonl(record: dict[str, Any], *, path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":"), sort_keys=True))
        f.write("\n")


def start_run(req: BetaRunStartRequest, *, now: float | None = None, path: str | None = None) -> BetaRun:
    ts = float(time.time() if now is None else now)
    run = BetaRun(
        run_id=str(uuid.uuid4()),
        project_id=req.project_id,
        project_name=req.project_name,
        environment=req.environment,
        status="running",
        correlation_id=req.correlation_id,
        triggered_by=req.triggered_by,
        labels=req.labels,
        details=req.details,
        started_at=ts,
        updated_at=ts,
        finished_at=None,
        finished_by=None,
    )
    _append_jsonl(run.model_dump(), path=path or _store_path())
    return run


def _load_latest_by_run_id(*, path: str) -> dict[str, dict[str, Any]]:
    if not os.path.exists(path):
        return {}

    latest: dict[str, dict[str, Any]] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                # Skip malformed lines; production should quarantine and alert.
                continue
            if obj.get("schema") != "gados.beta.run.v1":
                continue
            run_id = obj.get("run_id")
            if isinstance(run_id, str) and run_id:
                latest[run_id] = obj
    return latest


def complete_run(
    run_id: str,
    req: BetaRunCompleteRequest,
    *,
    now: float | None = None,
    path: str | None = None,
) -> BetaRun | None:
    store = path or _store_path()
    latest = _load_latest_by_run_id(path=store).get(run_id)
    if latest is None:
        return None

    ts = float(time.time() if now is None else now)
    updated = BetaRun.model_validate(
        {
            **latest,
            "status": req.status,
            "finished_by": req.finished_by,
            "details": {**(latest.get("details") or {}), **req.details},
            "finished_at": ts,
            "updated_at": ts,
        }
    )
    _append_jsonl(updated.model_dump(), path=store)
    return updated


def list_runs(
    *,
    limit: int = 50,
    project_id: str | None = None,
    path: str | None = None,
) -> list[BetaRun]:
    store = path or _store_path()
    latest = _load_latest_by_run_id(path=store)
    runs: list[dict[str, Any]] = list(latest.values())
    if project_id:
        runs = [r for r in runs if r.get("project_id") == project_id]
    runs.sort(key=lambda r: float(r.get("updated_at") or 0.0), reverse=True)
    return [BetaRun.model_validate(r) for r in runs[: max(0, int(limit))]]


def list_projects(
    *,
    limit: int = 50,
    path: str | None = None,
) -> list[dict[str, Any]]:
    """
    Returns a UI-friendly list of projects with their latest run snapshot.
    """
    store = path or _store_path()
    latest_by_run = _load_latest_by_run_id(path=store)
    latest_by_project: dict[str, dict[str, Any]] = {}

    for run in latest_by_run.values():
        pid = run.get("project_id")
        if not isinstance(pid, str) or not pid:
            continue
        prev = latest_by_project.get(pid)
        if prev is None:
            latest_by_project[pid] = run
            continue
        if float(run.get("updated_at") or 0.0) >= float(prev.get("updated_at") or 0.0):
            latest_by_project[pid] = run

    projects = list(latest_by_project.values())
    projects.sort(key=lambda r: float(r.get("updated_at") or 0.0), reverse=True)

    out: list[dict[str, Any]] = []
    for r in projects[: max(0, int(limit))]:
        out.append(
            {
                "project_id": r.get("project_id"),
                "project_name": r.get("project_name"),
                "latest_run": r,
            }
        )
    return out

