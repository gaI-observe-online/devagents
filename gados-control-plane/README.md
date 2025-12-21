# GADOS Control Plane (CA GUI)

This is a **free-stack**, self-hostable, interactive GUI for GADOS artifacts.

## Goals (MVP)
- Browse artifacts in `/gados-project/`
- Create epics/stories/change plans from templates
- Append to story audit logs (append-only)
- Validate governance rules (naming, required artifacts, verification gate prerequisites)

## Stack (cost-effective)
- **Backend**: FastAPI (Python)
- **UI**: Server-rendered HTML + **HTMX** (interactive without a JS build)
- **Styling**: Pico.css via CDN (free)
- **Storage**: Artifacts are files in git; optional SQLite later

## Run locally
From repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r gados-control-plane/requirements.txt
uvicorn gados_control_plane.main:app --reload --port 8000
```

Open: `http://localhost:8000`

## Governance note
This GUI does **not** “auto-verify” anything. It only helps produce and validate artifacts.
Only the **Delivery Governor (VDA)** may certify `VERIFIED` in the story log, and only with evidence + peer review present.

