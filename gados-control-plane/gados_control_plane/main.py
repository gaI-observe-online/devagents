from __future__ import annotations

import asyncio
import os
import secrets
import uuid
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware

from .agents_langgraph import run_daily_digest
from .bus import ack_message, list_inbox, send_message
from .artifacts import (
    append_text,
    list_artifacts,
    parse_story_status,
    read_text,
    write_text,
)
from .paths import get_paths
from .validator import format_text_report, validate

from gados_common.observability import instrument_fastapi, request_id_ctx, setup_observability
from opentelemetry import metrics, trace


app = FastAPI(title="GADOS Control Plane (CA GUI)", version="0.1.0")
basic_auth = HTTPBasic(auto_error=False)
_ready = False

PKG_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(PKG_DIR / "templates"))

static_dir = PKG_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

setup_observability(service_name="gados-control-plane")
instrument_fastapi(app)

_log = __import__("logging").getLogger(__name__)
_tracer = trace.get_tracer("gados-control-plane")
_meter = metrics.get_meter("gados-control-plane")
_debug_counter = _meter.create_counter(
    name="gados_debug_trace_total",
    description="Count of /debug/trace calls",
    unit="1",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def _auth_enabled() -> bool:
    return bool(os.getenv("GADOS_BASIC_AUTH_USER")) and bool(os.getenv("GADOS_BASIC_AUTH_PASSWORD"))

def _max_request_bytes() -> int:
    try:
        return int(os.getenv("GADOS_MAX_REQUEST_BYTES", "1048576"))
    except Exception:
        return 1048576

def _cors_allow_origins() -> list[str]:
    raw = os.getenv("GADOS_CORS_ALLOW_ORIGINS", "").strip()
    if not raw:
        return []
    return [o.strip() for o in raw.split(",") if o.strip()]


# CORS is explicit (empty => no CORS headers)
_origins = _cors_allow_origins()
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        max_age=600,
    )


# Basic request size cap (best-effort via Content-Length)
@app.middleware("http")
async def request_size_middleware(request: Request, call_next):
    max_bytes = _max_request_bytes()
    cl = request.headers.get("content-length")
    if cl:
        try:
            if int(cl) > max_bytes:
                raise HTTPException(status_code=413, detail="Request too large")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Content-Length")
    return await call_next(request)


# Simple per-process token-bucket rate limit (good enough for beta)
_rl_lock = threading.Lock()
_rl_state: dict[str, tuple[float, float]] = {}  # ip -> (tokens, last_ts)

def _rate_limit_params() -> tuple[float, float]:
    try:
        rps = float(os.getenv("GADOS_RATE_LIMIT_RPS", "10"))
    except Exception:
        rps = 10.0
    try:
        burst = float(os.getenv("GADOS_RATE_LIMIT_BURST", "20"))
    except Exception:
        burst = 20.0
    return max(0.1, rps), max(1.0, burst)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    rps, burst = _rate_limit_params()
    now = time.monotonic()
    ip = (request.client.host if request.client else "unknown")
    with _rl_lock:
        tokens, last = _rl_state.get(ip, (burst, now))
        # Refill
        tokens = min(burst, tokens + (now - last) * rps)
        if tokens < 1.0:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        tokens -= 1.0
        _rl_state[ip] = (tokens, now)
        # Best-effort pruning
        if len(_rl_state) > 5000:
            cutoff = now - 600.0
            for k, (_t, ts) in list(_rl_state.items()):
                if ts < cutoff:
                    _rl_state.pop(k, None)
    return await call_next(request)


def require_write_auth(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(basic_auth),
) -> str:
    """
    MVP access control for write endpoints.

    If auth env vars are set, require HTTP Basic auth and return the username.
    If unset, allow (insecure local mode) and return "anonymous".
    """
    if not _auth_enabled():
        return "anonymous"
    if credentials is None:
        _log.warning(
            "auth_missing",
            extra={"path": str(request.url.path), "client_ip": request.client.host if request.client else None},
        )
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Basic"})

    expected_user = os.getenv("GADOS_BASIC_AUTH_USER", "")
    expected_pass = os.getenv("GADOS_BASIC_AUTH_PASSWORD", "")
    user_ok = secrets.compare_digest(credentials.username, expected_user)
    pass_ok = secrets.compare_digest(credentials.password, expected_pass)
    if not (user_ok and pass_ok):
        _log.warning(
            "auth_failed",
            extra={
                "path": str(request.url.path),
                "client_ip": request.client.host if request.client else None,
                "username": credentials.username,
            },
        )
        raise HTTPException(status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Basic"})
    return credentials.username


async def _autorun_reports_loop() -> None:
    """
    Optional autonomous report generation loop.

    Controlled via env vars:
    - GADOS_AUTORUN_REPORTS=1 to enable
    - GADOS_AUTORUN_REPORTS_INTERVAL_MINUTES=360 (default 6 hours)
    """
    enabled = os.getenv("GADOS_AUTORUN_REPORTS", "0").strip() == "1"
    if not enabled:
        return
    interval_min = int(os.getenv("GADOS_AUTORUN_REPORTS_INTERVAL_MINUTES", "360"))
    interval_sec = max(60, interval_min * 60)
    while True:
        try:
            run_daily_digest()
        except Exception:
            # Best-effort: loop should never crash the server.
            pass
        await asyncio.sleep(interval_sec)


@app.on_event("startup")
async def _startup() -> None:
    global _ready
    # Touch the bus DB so readiness reflects basic runtime initialization.
    try:
        list_inbox(to_role="CoordinationAgent", to_agent_id="CA-1", limit=1)
    except Exception:
        # Don't block startup; readiness will still flip to READY.
        pass
    _ready = True
    asyncio.create_task(_autorun_reports_loop())


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


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    paths = get_paths()

    # Compute basic counts and story status distribution
    story_dir = paths.gados_root / "plan" / "stories"
    stories: list[dict] = []
    by_status: dict[str, int] = {}
    if story_dir.exists():
        for p in sorted(story_dir.iterdir()):
            if not (p.is_file() and p.name.startswith("STORY-") and p.suffix == ".md"):
                continue
            rel = str(p.relative_to(paths.gados_root))
            md = p.read_text(encoding="utf-8")
            status = parse_story_status(md) or "UNKNOWN"
            by_status[status] = by_status.get(status, 0) + 1
            stories.append({"id": p.stem, "rel": rel, "status": status})

    epic_dir = paths.gados_root / "strategy"
    epic_count = 0
    if epic_dir.exists():
        epic_count = len([p for p in epic_dir.iterdir() if p.is_file() and p.name.startswith("EPIC-") and p.suffix == ".md"])

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "epic_count": epic_count,
            "story_count": len(stories),
            "stories": stories[:30],
            "by_status": dict(sorted(by_status.items(), key=lambda kv: (-kv[1], kv[0]))),
        },
    )


@app.get("/health")
def health() -> dict[str, str | bool]:
    # Minimal readiness signal for beta runners/CI.
    return {
        "status": "READY" if _ready else "STARTING",
        "ready": _ready,
        "auth_enabled": _auth_enabled(),
    }


@app.get("/debug/trace")
def debug_trace() -> dict[str, bool]:
    with _tracer.start_as_current_span("debug.trace") as span:
        span.set_attribute("debug", True)
        _debug_counter.add(1)
        _log.info("debug_trace_called")
    return {"ok": True}


@app.get("/artifacts", response_class=HTMLResponse)
def artifacts(request: Request, dir: str = "") -> HTMLResponse:
    paths = get_paths()
    try:
        items = list_artifacts(paths, dir)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return templates.TemplateResponse(
        "artifacts.html",
        {"request": request, "dir": dir, "items": items},
    )


@app.get("/view", response_class=HTMLResponse)
def view(request: Request, path: str) -> HTMLResponse:
    paths = get_paths()
    try:
        content = read_text(paths, path)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return templates.TemplateResponse(
        "view.html",
        {"request": request, "path": path, "content": content},
    )


@app.get("/create", response_class=HTMLResponse)
def create_forms(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("create.html", {"request": request})


@app.post("/create/epic")
def create_epic(
    epic_id: str = Form(...),
    title: str = Form(...),
    owner: str = Form("Strategic Brain"),
    _user: str = Depends(require_write_auth),
) -> RedirectResponse:
    paths = get_paths()
    template_rel = "templates/EPIC.template.md"
    epic_rel = f"strategy/{epic_id}.md"
    tpl = read_text(paths, template_rel)
    content = tpl.replace("EPIC-###", epic_id).replace("<Epic Title>", title).replace("<name>", owner)
    write_text(paths, epic_rel, content)
    return RedirectResponse(url=f"/view?path={epic_rel}", status_code=303)


@app.post("/create/story")
def create_story(
    story_id: str = Form(...),
    title: str = Form(...),
    epic_id: str = Form(...),
    _user: str = Depends(require_write_auth),
) -> RedirectResponse:
    paths = get_paths()
    tpl = read_text(paths, "templates/STORY.template.md")
    story_rel = f"plan/stories/{story_id}.md"
    content = tpl.replace("STORY-###", story_id).replace("<Story Title>", title).replace("EPIC-###", epic_id)
    write_text(paths, story_rel, content)

    # Create a stub log file as well (append-only)
    log_rel = f"log/{story_id}.log.yaml"
    if not (paths.gados_root / log_rel).exists():
        log_tpl = read_text(paths, "templates/STORY.log.template.yaml")
        stub = (
            log_tpl.replace("STORY-###", story_id)
            .replace("EPIC-###", epic_id)
            .replace("<Story Title>", title)
            .replace("<ISO-8601 UTC timestamp>", _utc_now())
            .replace("<name>", "CoordinationAgent")
        )
        write_text(paths, log_rel, stub)

    return RedirectResponse(url=f"/view?path={story_rel}", status_code=303)


@app.post("/create/change")
def create_change(
    change_id: str = Form(...),
    story_id: str = Form(...),
    epic_id: str = Form(...),
    title: str = Form(...),
    _user: str = Depends(require_write_auth),
) -> RedirectResponse:
    paths = get_paths()
    tpl = read_text(paths, "templates/CHANGE.template.yaml")
    rel = f"plan/changes/{change_id}.yaml"
    content = (
        tpl.replace("CHANGE-###-A", change_id)
        .replace("STORY-###", story_id)
        .replace("EPIC-###", epic_id)
        .replace("<Change Plan Title>", title)
    )
    write_text(paths, rel, content)
    return RedirectResponse(url=f"/view?path={rel}", status_code=303)


@app.get("/decisions", response_class=HTMLResponse)
def decisions(request: Request) -> HTMLResponse:
    paths = get_paths()
    decision_dir = paths.gados_root / "decision"
    items: list[str] = []
    if decision_dir.exists():
        for p in sorted(decision_dir.iterdir(), reverse=True):
            if not p.is_file():
                continue
            if p.name == "README.md":
                continue
            items.append(str(p.relative_to(paths.gados_root)))
    return templates.TemplateResponse("decisions.html", {"request": request, "items": items})


@app.post("/create/adr")
def create_adr(
    adr_id: str = Form(...),
    title: str = Form(...),
    human: str = Form(...),
    requested_by: str = Form(...),
    user: str = Depends(require_write_auth),
) -> RedirectResponse:
    paths = get_paths()
    tpl = read_text(paths, "templates/ADR.template.md")
    today = datetime.now(timezone.utc).date().isoformat()
    content = (
        tpl.replace("ADR-###", adr_id)
        .replace("<Decision Title>", title)
        .replace("<name>", human)
        .replace("<role/agent>", requested_by)
        .replace("<YYYY-MM-DD>", today)
    )
    rel = f"decision/{adr_id}.md"
    # Lightweight attribution for audit trail.
    content = content + f"\n\n---\n**submitted_by**: {user}\n**submitted_at_utc**: {_utc_now()}\n"
    write_text(paths, rel, content)
    return RedirectResponse(url=f"/view?path={rel}", status_code=303)


@app.post("/append/story-log")
def append_story_log(
    story_id: str = Form(...),
    actor_role: str = Form(...),
    actor: str = Form(...),
    event_type: str = Form(...),
    notes: str = Form(""),
    user: str = Depends(require_write_auth),
) -> RedirectResponse:
    paths = get_paths()
    log_rel = f"log/{story_id}.log.yaml"
    notes_safe = notes.replace('"', "'")
    entry = (
        "\n"
        "  - at: \"" + _utc_now() + "\"\n"
        "    actor_role: \"" + actor_role + "\"\n"
        "    actor: \"" + actor + "\"\n"
        "    type: \"" + event_type + "\"\n"
        "    notes: \"" + notes_safe + "\"\n"
        "    submitted_by: \"" + user.replace('"', "'") + "\"\n"
    )
    append_text(paths, log_rel, entry)
    return RedirectResponse(url=f"/view?path={log_rel}", status_code=303)


@app.get("/validate", response_class=HTMLResponse)
def validate_ui(request: Request) -> HTMLResponse:
    paths = get_paths()
    msgs = validate(paths)
    return templates.TemplateResponse("validate.html", {"request": request, "messages": msgs})


@app.get("/validate.txt", response_class=PlainTextResponse)
def validate_txt() -> PlainTextResponse:
    paths = get_paths()
    msgs = validate(paths)
    return PlainTextResponse(format_text_report(msgs))


@app.get("/reports", response_class=HTMLResponse)
def reports(request: Request) -> HTMLResponse:
    paths = get_paths()
    reports_dir = paths.gados_root / "log" / "reports"
    reports_list: list[dict] = []
    if reports_dir.exists():
        for p in sorted(reports_dir.iterdir(), reverse=True):
            if not (p.is_file() and p.suffix == ".md" and p.name.startswith("REPORT-")):
                continue
            reports_list.append(
                {
                    "name": p.name,
                    "rel": str(p.relative_to(paths.gados_root)),
                }
            )
    return templates.TemplateResponse("reports.html", {"request": request, "reports": reports_list})


@app.post("/agents/run/daily-digest")
def run_agents_daily_digest(_user: str = Depends(require_write_auth)) -> RedirectResponse:
    out = run_daily_digest()
    rel = out.get("report_rel_path", "log/reports")
    return RedirectResponse(url=f"/view?path={rel}", status_code=303)


@app.get("/inbox", response_class=HTMLResponse)
def inbox(request: Request, role: str = "CoordinationAgent", agent_id: str = "CA-1") -> HTMLResponse:
    msgs = list_inbox(to_role=role, to_agent_id=agent_id, limit=100)
    return templates.TemplateResponse(
        "inbox.html",
        {"request": request, "role": role, "agent_id": agent_id, "messages": msgs},
    )


@app.post("/bus/send")
def bus_send(
    from_role: str = Form(...),
    from_agent_id: str = Form(...),
    to_role: str = Form(...),
    to_agent_id: str = Form(...),
    type: str = Form(...),
    severity: str = Form("INFO"),
    story_id: str = Form(""),
    epic_id: str = Form(""),
    notes: str = Form(""),
    user: str = Depends(require_write_auth),
) -> RedirectResponse:
    send_message(
        from_role=from_role,
        from_agent_id=from_agent_id,
        to_role=to_role,
        to_agent_id=to_agent_id,
        type=type,
        severity=severity,  # type: ignore[arg-type]
        story_id=story_id or None,
        epic_id=epic_id or None,
        payload={"notes": notes, "submitted_by": user, "submitted_at_utc": _utc_now()} if notes or user else {},
    )
    return RedirectResponse(url=f"/inbox?role={to_role}&agent_id={to_agent_id}", status_code=303)


@app.post("/bus/ack")
def bus_ack(
    message_id: str = Form(...),
    status: str = Form(...),
    actor_role: str = Form(...),
    actor_id: str = Form(...),
    notes: str = Form(""),
    redirect_role: str = Form("CoordinationAgent"),
    redirect_agent_id: str = Form("CA-1"),
    user: str = Depends(require_write_auth),
) -> RedirectResponse:
    ack_message(
        message_id=message_id,
        status=status,  # type: ignore[arg-type]
        actor_role=actor_role,
        actor_id=actor_id,
        notes=(notes + f" (submitted_by={user})").strip(),
    )
    return RedirectResponse(url=f"/inbox?role={redirect_role}&agent_id={redirect_agent_id}", status_code=303)

