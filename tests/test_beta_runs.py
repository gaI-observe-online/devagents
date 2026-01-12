from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_beta_runs_are_visible_for_ui(monkeypatch, tmp_path: Path):
    store = tmp_path / "beta_runs.jsonl"
    monkeypatch.setenv("GADOS_BETA_RUN_STORE_PATH", str(store))

    client = TestClient(app)

    r1 = client.post(
        "/beta/runs",
        json={
            "project_id": "proj_a",
            "project_name": "Project A",
            "environment": "test",
            "triggered_by": "pytest",
            "labels": {"suite": "unit"},
        },
    )
    assert r1.status_code == 200
    run_a = r1.json()
    assert run_a["project_id"] == "proj_a"
    assert run_a["environment"] == "test"
    assert run_a["status"] == "running"

    r2 = client.post(
        "/beta/runs",
        json={"project_id": "proj_b", "project_name": "Project B", "environment": "test"},
    )
    assert r2.status_code == 200

    done = client.post(
        f"/beta/runs/{run_a['run_id']}/complete",
        json={"status": "succeeded", "finished_by": "pytest"},
    )
    assert done.status_code == 200
    assert done.json()["status"] == "succeeded"
    assert done.json()["finished_at"] is not None

    runs = client.get("/beta/runs", params={"limit": 10})
    assert runs.status_code == 200
    runs_json = runs.json()
    assert len(runs_json) == 2
    assert {r["project_id"] for r in runs_json} == {"proj_a", "proj_b"}
    a = next(r for r in runs_json if r["project_id"] == "proj_a")
    assert a["status"] == "succeeded"

    projects = client.get("/beta/projects", params={"limit": 10})
    assert projects.status_code == 200
    projects_json = projects.json()
    assert {p["project_id"] for p in projects_json} == {"proj_a", "proj_b"}
    a_proj = next(p for p in projects_json if p["project_id"] == "proj_a")
    assert a_proj["latest_run"]["status"] == "succeeded"

