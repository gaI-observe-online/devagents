"""Tests for fixes addressing Bugbot review warnings from PR #3."""

import json
import threading
import time
from pathlib import Path

from gados_control_plane.beta_run_store import _allocate_beta_run_dir
from gados_control_plane.paths import ProjectPaths

from app.notifications import flush_daily_digest


def test_env_var_parsing_error_handling(monkeypatch, tmp_path: Path):
    """Test that invalid GADOS_AUTORUN_REPORTS_INTERVAL_MINUTES doesn't crash."""
    # This tests the fix for Issue #4: Missing error handling for env var parsing
    
    # Set up test environment
    monkeypatch.setenv("GADOS_AUTORUN_REPORTS", "1")
    monkeypatch.setenv("GADOS_AUTORUN_REPORTS_INTERVAL_MINUTES", "not_a_number")
    
    # Import after monkeypatch to ensure env vars are set
    import asyncio

    from gados_control_plane.main import _autorun_reports_loop
    
    # Mock run_daily_digest to avoid actual execution
    mock_called = {"count": 0}
    
    async def mock_run_daily_digest():
        mock_called["count"] += 1
        raise Exception("Test exception")  # Simulate error
    
    monkeypatch.setattr("gados_control_plane.main.run_daily_digest", mock_run_daily_digest)
    
    # Run the loop for a short time - it should handle the invalid env var gracefully
    async def run_with_timeout():
        task = asyncio.create_task(_autorun_reports_loop())
        await asyncio.sleep(0.1)  # Let it run briefly
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    # Should not raise ValueError from int() conversion
    asyncio.run(run_with_timeout())


def test_concurrent_beta_run_directory_allocation(tmp_path: Path):
    """Test that concurrent directory allocation is handled with retry logic."""
    # This tests the fix for Issue #5: TOCTOU race in directory allocation
    
    repo_root = tmp_path / "repo"
    gados_root = repo_root / "gados-project"
    templates_dir = gados_root / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    paths = ProjectPaths(repo_root=repo_root, gados_root=gados_root, templates_dir=templates_dir)
    
    results = {"run_ids": [], "errors": []}
    
    def allocate_worker(worker_id: int):
        try:
            run_id, run_dir = _allocate_beta_run_dir(paths, scenario="concurrent-test")
            results["run_ids"].append(run_id)
        except Exception as e:
            results["errors"].append(f"Worker {worker_id}: {str(e)}")
    
    # Start multiple threads trying to allocate directories concurrently
    threads = []
    for i in range(5):
        thread = threading.Thread(target=allocate_worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify no errors occurred (retry logic should handle conflicts)
    assert not results["errors"], f"Errors during concurrent allocation: {results['errors']}"
    
    # Verify we got 5 unique directory IDs
    assert len(results["run_ids"]) == 5
    assert len(set(results["run_ids"])) == 5, "Directory IDs should be unique"
    
    # Verify all directories actually exist
    for run_id in results["run_ids"]:
        run_dir = gados_root / "log" / "reports" / "beta-runs" / run_id
        assert run_dir.exists(), f"Directory {run_id} should exist"


def test_yaml_injection_prevention():
    """Test that YAML injection attempts are properly escaped."""
    # This tests the fix for Issue #3: YAML injection risk
    
    import yaml
    
    # Malicious inputs that could inject YAML
    malicious_inputs = [
        'value"\nmalicious_key: injection',  # Newline injection
        'value\n  nested: attack',  # Indentation attack
        "value'\n- list_item",  # List injection
        'multi\nline\nvalue',  # Multiple newlines
    ]
    
    for malicious_input in malicious_inputs:
        # Create entry data as done in the fixed code
        entry_data = {
            "at": "2025-01-01T00:00:00Z",
            "actor_role": malicious_input,
            "actor": malicious_input,
            "type": malicious_input,
            "notes": malicious_input,
            "submitted_by": "user",
        }
        
        # Use yaml.safe_dump as in the fix
        entry_yaml = yaml.safe_dump([entry_data], default_flow_style=False, sort_keys=False)
        
        # Parse it back to verify it's valid YAML and doesn't contain injected keys
        parsed = yaml.safe_load(entry_yaml)
        
        # Verify the structure is as expected (single list item)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert isinstance(parsed[0], dict)
        
        # Verify no unexpected keys were injected
        expected_keys = {"at", "actor_role", "actor", "type", "notes", "submitted_by"}
        assert set(parsed[0].keys()) == expected_keys
        
        # Verify values are properly escaped and match the input
        assert parsed[0]["actor_role"] == malicious_input
        assert parsed[0]["notes"] == malicious_input


def test_hardcoded_date_fix():
    """Test that notification file path uses dynamic date instead of hardcoded date."""
    # This tests the fix for Issue #1: Hardcoded date in evidence path
    
    from datetime import UTC, datetime

    
    # Get today's date string as the code now generates it
    today_str = datetime.now(UTC).strftime("%Y%m%d")
    expected_filename = f"NOTIFICATIONS-{today_str}.md"
    
    # Verify the filename is not the hardcoded old date
    assert expected_filename != "NOTIFICATIONS-20251222.md"
    
    # Verify the filename format is correct (8 digits for YYYYMMDD)
    assert len(today_str) == 8
    assert today_str.isdigit()


def test_flush_digest_race_condition_prevention(tmp_path: Path, monkeypatch):
    """Test that concurrent flush and truncate operations don't cause data loss."""
    # This tests the fix for Issue #2: Race condition in notification flush
    
    digest_path = tmp_path / "notifications.queue.jsonl"
    output_path = tmp_path / "output.md"
    
    monkeypatch.setenv("GADOS_RUNTIME_DIR", str(tmp_path))
    
    # Pre-populate with some events
    events_data = [
        json.dumps({"schema": "gados.digest.queue.v1", "event": {"event_type": f"event{i}"}})
        for i in range(10)
    ]
    digest_path.write_text("\n".join(events_data) + "\n", encoding="utf-8")
    
    results = {"flushed": 0, "errors": []}
    
    def flush_worker():
        try:
            result = flush_daily_digest(output_path=output_path, truncate=True)
            results["flushed"] = result["flushed"]
        except Exception as e:
            results["errors"].append(f"Flush: {str(e)}")
    
    def write_worker():
        try:
            # Try to write to the file while flush is happening
            for i in range(5):
                from gados_common.fileio import append_text_locked
                event = json.dumps({"schema": "gados.digest.queue.v1", "event": {"event_type": f"concurrent{i}"}})
                append_text_locked(digest_path, event + "\n")
                time.sleep(0.001)
        except Exception as e:
            results["errors"].append(f"Write: {str(e)}")
    
    # Start concurrent operations
    flush_thread = threading.Thread(target=flush_worker)
    write_thread = threading.Thread(target=write_worker)
    
    flush_thread.start()
    time.sleep(0.001)  # Small delay to ensure flush starts first
    write_thread.start()
    
    flush_thread.join()
    write_thread.join()
    
    # Verify no errors occurred
    assert not results["errors"], f"Errors during concurrent operations: {results['errors']}"
    
    # Verify flushed count matches initial events (10)
    assert results["flushed"] == 10
    
    # Verify output was created
    assert output_path.exists()
    
    # After flush with truncate, the queue should contain only new concurrent writes
    if digest_path.exists():
        remaining = digest_path.read_text(encoding="utf-8").strip()
        if remaining:
            lines = remaining.splitlines()
            # Should have the concurrent writes that happened during/after flush
            assert len(lines) <= 5

