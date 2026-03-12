"""Tests for agent endpoints: tool registry, race brief, context packs."""

from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

# ── Shared test snapshot ──────────────────────────────────────────────────

SAMPLE_SNAPSHOT = {
    "session_id": "test_session",
    "timestamp_utc": "2026-02-28T06:00:00Z",
    "lap": 18,
    "track_status": {"sc": False, "vsc": False, "flag": "GREEN"},
    "drivers": [
        {"driver_code": "VER", "position": 1, "gap_to_leader": 0.0,
         "gap_ahead": None, "gap_behind": 1.2, "tire": {"compound": "MED", "age": 12},
         "last_lap_time": 79.5},
        {"driver_code": "NOR", "position": 2, "gap_to_leader": 1.2,
         "gap_ahead": 1.2, "gap_behind": 2.1, "tire": {"compound": "MED", "age": 12},
         "last_lap_time": 80.1},
        {"driver_code": "LEC", "position": 3, "gap_to_leader": 3.3,
         "gap_ahead": 2.1, "gap_behind": 5.0, "tire": {"compound": "HARD", "age": 5},
         "last_lap_time": 80.4},
        {"driver_code": "PIA", "position": 4, "gap_to_leader": 8.3,
         "gap_ahead": 5.0, "gap_behind": 1.0, "tire": {"compound": "MED", "age": 15},
         "last_lap_time": 81.2},
        {"driver_code": "ALO", "position": 5, "gap_to_leader": 9.3,
         "gap_ahead": 1.0, "gap_behind": 3.0, "tire": None,
         "last_lap_time": 81.8},
        {"driver_code": "SAI", "position": 6, "gap_to_leader": 12.3,
         "gap_ahead": 3.0, "gap_behind": None, "tire": None,
         "last_lap_time": 82.0},
    ],
}

SAMPLE_PACE = [79.5, 80.0, 79.8, 80.1]


# ── /agent/tools ──────────────────────────────────────────────────────────

def test_agent_tools_returns_registry():
    resp = client.get("/agent/tools")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "v1"
    assert isinstance(data["tools"], list)
    names = {t["name"] for t in data["tools"]}
    assert "project_pit_rejoin" in names
    assert "estimate_undercut" in names
    for t in data["tools"]:
        assert isinstance(t["input_schema"], dict)
        assert isinstance(t["output_schema"], dict)


# ── /agent/race_brief ────────────────────────────────────────────────────

@patch("app.deps.session_exists")
@patch("app.services.race_brief_service.get_latest_snapshot")
def test_race_brief_basic(mock_snap, mock_exists):
    mock_exists.return_value = True
    mock_snap.return_value = SAMPLE_SNAPSHOT

    resp = client.post("/agent/race_brief", json={
        "session_id": "test_session",
        "focus_driver": "NOR",
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["lap"] == 18
    assert "timestamp_utc" in data
    assert len(data["top5"]) <= 5
    assert data["top5"][0]["driver_code"] == "VER"
    assert data["focus"]["driver_code"] == "NOR"
    assert data["focus"]["position"] == 2


@patch("app.deps.session_exists")
@patch("app.services.race_brief_service.get_latest_snapshot")
def test_race_brief_409_when_no_snapshot(mock_snap, mock_exists):
    mock_exists.return_value = True
    mock_snap.return_value = None

    resp = client.post("/agent/race_brief", json={"session_id": "test_session"})
    assert resp.status_code == 409


# ── /agent/context_pack ──────────────────────────────────────────────────

@patch("app.deps.session_exists")
@patch("app.services.context_pack_service.get_latest_snapshot")
@patch("app.services.context_pack_service.get_pace_history")
def test_context_pack_undercut(mock_pace, mock_snap, mock_exists):
    mock_exists.return_value = True
    mock_snap.return_value = SAMPLE_SNAPSHOT
    mock_pace.return_value = SAMPLE_PACE

    resp = client.post("/agent/context_pack", json={
        "session_id": "test_session",
        "query_type": "undercut",
        "drivers": ["NOR", "LEC"],
        "horizon_laps": 3,
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["query_type"] == "undercut"
    assert data["attacker_pace_median_s"] is not None
    assert data["defender_pace_median_s"] is not None
    assert data["pit_loss_s"] == 21.0
    assert data["new_tire_delta_s_per_lap"] == 0.6
    assert data["horizon_laps"] == 3


@patch("app.deps.session_exists")
@patch("app.services.context_pack_service.get_latest_snapshot")
def test_context_pack_pit_rejoin(mock_snap, mock_exists):
    mock_exists.return_value = True
    mock_snap.return_value = SAMPLE_SNAPSHOT

    resp = client.post("/agent/context_pack", json={
        "session_id": "test_session",
        "query_type": "pit_rejoin",
        "drivers": ["NOR"],
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["query_type"] == "pit_rejoin"
    assert data["target_driver"]["driver_code"] == "NOR"
    assert len(data["position_window"]) > 0
    assert data["pit_loss_s"] == 21.0
