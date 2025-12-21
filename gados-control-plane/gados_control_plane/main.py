from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
def health() -> dict[str, str]:
    return {"status": "ok"}


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
def create_epic(epic_id: str = Form(...), title: str = Form(...), owner: str = Form("Strategic Brain")) -> RedirectResponse:
    paths = get_paths()
    template_rel = "templates/EPIC.template.md"
    epic_rel = f"strategy/{epic_id}.md"
    tpl = read_text(paths, template_rel)
    content = tpl.replace("EPIC-###", epic_id).replace("<Epic Title>", title).replace("<name>", owner)
    write_text(paths, epic_rel, content)
    return RedirectResponse(url=f"/view?path={epic_rel}", status_code=303)


@app.post("/create/story")
def create_story(story_id: str = Form(...), title: str = Form(...), epic_id: str = Form(...)) -> RedirectResponse:
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
def create_change(change_id: str = Form(...), story_id: str = Form(...), epic_id: str = Form(...), title: str = Form(...)) -> RedirectResponse:
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
def create_adr(adr_id: str = Form(...), title: str = Form(...), human: str = Form(...), requested_by: str = Form(...)) -> RedirectResponse:
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
    write_text(paths, rel, content)
    return RedirectResponse(url=f"/view?path={rel}", status_code=303)


@app.post("/append/story-log")
def append_story_log(
    story_id: str = Form(...),
    actor_role: str = Form(...),
    actor: str = Form(...),
    event_type: str = Form(...),
    notes: str = Form(""),
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
def run_agents_daily_digest() -> RedirectResponse:
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
        payload={"notes": notes} if notes else {},
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
) -> RedirectResponse:
    ack_message(
        message_id=message_id,
        status=status,  # type: ignore[arg-type]
        actor_role=actor_role,
        actor_id=actor_id,
        notes=notes,
    )
    return RedirectResponse(url=f"/inbox?role={redirect_role}&agent_id={redirect_agent_id}", status_code=303)

