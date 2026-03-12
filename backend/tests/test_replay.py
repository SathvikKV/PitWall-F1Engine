import pytest
import os
import json
import asyncio
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

TEST_SESSION_ID = "test_replay_session"

@pytest.fixture
def dummy_ndjson_path(tmp_path):
    path = tmp_path / "test_race.ndjson"
    snapshots = [
        {"session_id": TEST_SESSION_ID, "timestamp_utc": "1", "lap": 1, "track_status": {"flag": "GREEN"}, "drivers": []},
        {"session_id": TEST_SESSION_ID, "timestamp_utc": "2", "lap": 2, "track_status": {"flag": "GREEN"}, "drivers": []},
    ]
    with open(path, "w") as f:
        for s in snapshots:
            f.write(json.dumps(s) + "\n")
    return str(path)

@pytest.mark.asyncio
@patch("app.api.routes_admin.start_replay")
@patch("app.api.routes_admin.stop_replay")
@patch("app.api.routes_admin.get_replay_status")
@patch("app.deps.session_exists")
@patch("app.api.routes_tools.get_latest_snapshot")
async def test_replay_worker_flow(
    mock_get_snapshot, mock_exists, mock_status, mock_stop, mock_start, dummy_ndjson_path
):
    # Pre-test: endpoint returns 404 because session does not exist
    mock_exists.return_value = False
    resp = client.post("/tools/get_race_context", json={"session_id": TEST_SESSION_ID})
    assert resp.status_code == 404

    # 1. Start Replay
    mock_start.return_value = True
    resp = client.post("/admin/replay/start", json={
        "session_id": TEST_SESSION_ID,
        "ndjson_path": dummy_ndjson_path,
        "tick_ms": 50, 
        "loop": False
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"
    
    # 3. Test Snapshot exists and Context returns real data
    mock_exists.return_value = True
    mock_get_snapshot.return_value = {
        "lap": 2, 
        "track_status": {"flag": "GREEN"}, 
        "timestamp_utc": "2"
    }
    
    resp_ctx = client.post("/tools/get_race_context", json={"session_id": TEST_SESSION_ID})
    
    assert resp_ctx.status_code == 200
    data = resp_ctx.json()
    assert data["lap"] == 2
    assert data["source"] == "replay|live"
    
    # 4. Check Status
    mock_status.return_value = {"running": True, "idx": 1}
    resp_status = client.get(f"/admin/replay/status?session_id={TEST_SESSION_ID}")
    assert resp_status.status_code == 200
    
    # 5. Stop Replay
    mock_stop.return_value = True
    resp_stop = client.post("/admin/replay/stop", json={"session_id": TEST_SESSION_ID})
    assert resp_stop.status_code == 200
    assert resp_stop.json()["status"] == "stopped"
