from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from .artifacts import write_text
from .paths import get_paths
from .reporting import compute_metrics, render_daily_report_md
from .validator import validate


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ReportState(TypedDict, total=False):
    now_utc_iso: str
    metrics: dict[str, Any]
    validations: list[dict[str, Any]]
    report_md: str
    report_rel_path: str


def _strategic_brain_plan(state: ReportState) -> ReportState:
    # For now: no LLM usage. This node is a placeholder for future economics/architecture insights.
    state["now_utc_iso"] = state.get("now_utc_iso") or _utc_now_iso()
    return state


def _coordination_agent_collect(state: ReportState) -> ReportState:
    paths = get_paths()
    m = compute_metrics(paths)
    state["metrics"] = {
        "epic_count": m.epic_count,
        "story_count": m.story_count,
        "stories_by_status": m.stories_by_status,
        "verified_story_count": m.verified_story_count,
        "avg_time_to_verified_hours": m.avg_time_to_verified_hours,
        "validation_errors": m.validation_errors,
        "validation_warnings": m.validation_warnings,
    }
    return state


def _qa_agent_evidence(state: ReportState) -> ReportState:
    # QA agent in this context = evidence of governance compliance (validator output).
    paths = get_paths()
    msgs = validate(paths)
    state["validations"] = [
        {"level": m.level, "code": m.code, "message": m.message, "artifact": m.artifact} for m in msgs
    ]
    return state


def _peer_reviewer_assess(state: ReportState) -> ReportState:
    # Peer reviewer placeholder: could add drift analysis later (naming, directory compliance, etc.)
    return state


def _delivery_governor_render(state: ReportState) -> ReportState:
    # VDA produces a report artifact; it does NOT certify feature verification here.
    now = state.get("now_utc_iso") or _utc_now_iso()
    metrics = state.get("metrics") or {}
    validations_raw = state.get("validations") or []

    # Rehydrate into expected shapes for renderer
    # (Renderer expects ValidationMessage-like fields; we pass dicts with same keys.)
    report_md = render_daily_report_md(
        now_utc_iso=now,
        metrics=_MetricsShim.from_dict(metrics),
        validations=[_ValidationShim(**v) for v in validations_raw],
    )
    state["report_md"] = report_md
    return state


def _coordination_agent_write(state: ReportState) -> ReportState:
    paths = get_paths()
    now = state.get("now_utc_iso") or _utc_now_iso()
    # Keep history by stamping to seconds: REPORT-YYYYMMDD-HHMMSS.md
    dt_part = now.split("+", 1)[0].replace(":", "")
    date, time = dt_part.split("T", 1)
    stamp = f"{date.replace('-', '')}-{time}"
    rel = f"log/reports/REPORT-{stamp}.md"
    write_text(paths, rel, state.get("report_md", ""))
    state["report_rel_path"] = rel
    return state


@dataclass(frozen=True)
class _MetricsShim:
    epic_count: int
    story_count: int
    stories_by_status: dict[str, int]
    verified_story_count: int
    avg_time_to_verified_hours: float | None
    validation_errors: int
    validation_warnings: int

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "_MetricsShim":
        return _MetricsShim(
            epic_count=int(d.get("epic_count", 0)),
            story_count=int(d.get("story_count", 0)),
            stories_by_status=dict(d.get("stories_by_status", {})),
            verified_story_count=int(d.get("verified_story_count", 0)),
            avg_time_to_verified_hours=d.get("avg_time_to_verified_hours", None),
            validation_errors=int(d.get("validation_errors", 0)),
            validation_warnings=int(d.get("validation_warnings", 0)),
        )


@dataclass(frozen=True)
class _ValidationShim:
    level: str
    code: str
    message: str
    artifact: str | None = None


def build_daily_digest_graph():
    g = StateGraph(ReportState)
    g.add_node("StrategicBrain", _strategic_brain_plan)
    g.add_node("CoordinationAgentCollect", _coordination_agent_collect)
    g.add_node("QAAgent", _qa_agent_evidence)
    g.add_node("PeerReviewer", _peer_reviewer_assess)
    g.add_node("DeliveryGovernor", _delivery_governor_render)
    g.add_node("CoordinationAgentWrite", _coordination_agent_write)

    g.set_entry_point("StrategicBrain")
    g.add_edge("StrategicBrain", "CoordinationAgentCollect")
    g.add_edge("CoordinationAgentCollect", "QAAgent")
    g.add_edge("QAAgent", "PeerReviewer")
    g.add_edge("PeerReviewer", "DeliveryGovernor")
    g.add_edge("DeliveryGovernor", "CoordinationAgentWrite")
    g.add_edge("CoordinationAgentWrite", END)
    return g.compile()


def run_daily_digest() -> dict[str, Any]:
    """
    Run the LangGraph daily digest and return the resulting state.
    """
    graph = build_daily_digest_graph()
    state: ReportState = {"now_utc_iso": _utc_now_iso()}
    out = graph.invoke(state)
    return dict(out)

