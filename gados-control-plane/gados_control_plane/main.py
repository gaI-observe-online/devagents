from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .agents_langgraph import run_daily_digest
from .artifacts import (
    append_text,
    list_artifacts,
    parse_story_status,
    read_text,
    write_text,
)
from .paths import get_paths
from .validator import format_text_report, validate


app = FastAPI(title="GADOS Control Plane (CA GUI)", version="0.1.0")

PKG_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(PKG_DIR / "templates"))

static_dir = PKG_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


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

