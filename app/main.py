from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from gados_common.analytics import track_event
from gados_common.observability import instrument_fastapi, request_id_ctx, setup_observability

setup_observability(service_name="example-api")

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

