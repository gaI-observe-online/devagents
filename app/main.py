import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.analytics import track_event
from app.beta_runs import (
    BetaRun,
    BetaRunCompleteRequest,
    BetaRunStartRequest,
    complete_run,
    list_projects,
    list_runs,
    start_run,
)
from app.observability import instrument_fastapi, request_id_ctx, setup_observability

# Default to the canonical name used in runbooks; may be overridden by OTEL_SERVICE_NAME.
setup_observability(service_name="gados-control-plane")

log = logging.getLogger(__name__)
app = FastAPI(title="Example API (Analytics + Observability)")
instrument_fastapi(app)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    token = request_id_ctx.set(rid)
    try:
        response = await call_next(request)
        response.headers["x-request-id"] = rid
        return response
    finally:
        request_id_ctx.reset(token)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/health")
def health() -> dict[str, str]:
    # Alias to satisfy integration smoke checks expecting /health.
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    log.info("root_called")
    return {"hello": "world"}


class TrackRequest(BaseModel):
    event: str = Field(min_length=1)
    user_id: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


@app.post("/track")
def track(body: TrackRequest) -> dict[str, bool]:
    track_event(body.event, user_id=body.user_id, properties=body.properties)
    return {"accepted": True}


@app.post("/beta/runs")
def beta_run_start(body: BetaRunStartRequest) -> BetaRun:
    """
    Create a Beta/Test run record for UI visibility.
    """
    return start_run(body)


@app.post("/beta/runs/{run_id}/complete")
def beta_run_complete(run_id: str, body: BetaRunCompleteRequest) -> BetaRun:
    updated = complete_run(run_id, body)
    if updated is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    return updated


@app.get("/beta/runs")
def beta_run_list(project_id: str | None = None, limit: int = 50) -> list[BetaRun]:
    return list_runs(project_id=project_id, limit=limit)


@app.get("/beta/projects")
def beta_projects_list(limit: int = 50) -> list[dict[str, Any]]:
    """
    UI-friendly view: each project with its latest run snapshot.
    """
    return list_projects(limit=limit)
