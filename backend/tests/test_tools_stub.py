from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

@patch("app.deps.session_exists")
@patch("app.api.routes_tools.get_latest_snapshot")
def test_resolve_driver_session_exists(mock_snapshot, mock_exists):
    mock_exists.return_value = True
    mock_snapshot.return_value = {"timestamp_utc": "2024-03-24T05:22:10Z"}
    
    response = client.post("/tools/resolve_driver", json={
        "session_id": "test_session",
        "driver_reference": "Max"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["driver_code"] == "UNK"
    assert data["source"] == "replay|live"
    assert "timestamp_utc" in data

@patch("app.deps.session_exists")
def test_resolve_driver_session_missing(mock_exists):
    mock_exists.return_value = False
    response = client.post("/tools/resolve_driver", json={
        "session_id": "test_session",
        "driver_reference": "Max"
    })
    assert response.status_code == 404
    data = response.json()
    assert "error" in data["detail"]
    assert data["detail"]["error"] == "session_not_found"

def test_resolve_driver_missing_body_fields():
    response = client.post("/tools/resolve_driver", json={
        "driver_reference": "Max"
    })
    assert response.status_code == 400


# ── Pit Rejoin Integration ───────────────────────────────────────────────

SAMPLE_SNAPSHOT = {
    "session_id": "test_session",
    "timestamp_utc": "2026-02-28T06:00:00Z",
    "lap": 18,
    "mode": "replay",
    "ingest_ts_utc": "2026-02-28T06:00:01Z",
    "source_ts_utc": "2024-03-24T05:22:10Z",
    "track_status": {"sc": False, "vsc": False, "flag": "GREEN"},
    "drivers": [
        {
            "driver_code": "VER",
            "position": 1,
            "gap_to_leader": 0.0,
            "gap_behind": 1.5,
            "tire": {"compound": "MED", "age": 14},
            "last_lap_time": 91.3,
        },
        {
            "driver_code": "NOR",
            "position": 2,
            "gap_to_leader": 5.0,
            "gap_ahead": 1.5,
            "gap_behind": 0.9,
            "tire": {"compound": "MED", "age": 16},
            "last_lap_time": 90.5,
        },
        {
            "driver_code": "LEC",
            "position": 3,
            "gap_to_leader": 10.0,
            "gap_ahead": 5.0,
            "gap_behind": 20.0,
            "tire": {"compound": "HARD", "age": 8},
            "last_lap_time": 91.0,
        },
        {
            "driver_code": "PIA",
            "position": 4,
            "gap_to_leader": 30.0,
            "gap_ahead": 20.0,
            "tire": {"compound": "MED", "age": 10},
            "last_lap_time": 89.8,
        },
    ],
}

PACE_HISTORY = {
    "VER": [91.2, 91.4, 91.3, 91.5],
    "NOR": [90.4, 90.6, 90.5, 90.7],
    "LEC": [90.9, 91.0, 91.1, 91.0],
    "PIA": [89.6, 89.8, 89.7, 89.9],
}


@patch("app.deps.session_exists")
@patch("app.api.routes_tools.get_latest_snapshot")
def test_pit_rejoin_returns_real_position(mock_snapshot, mock_exists):
    mock_exists.return_value = True
    mock_snapshot.return_value = SAMPLE_SNAPSHOT

    response = client.post("/tools/project_pit_rejoin", json={
        "session_id": "test_session",
        "driver_code": "NOR",
    })
    assert response.status_code == 200
    data = response.json()

    assert data["projected_position"] is not None
    assert data["projected_position"] == 3  # behind VER (0) & LEC (10), ahead of PIA (30)
    assert data["confidence"] in ("low", "medium")
    assert "timestamp_utc" in data
    assert data["assumptions"]["pit_lane_loss_s"] == 21.0
    assert data["source"] == "replay"


@patch("app.deps.session_exists")
@patch("app.api.routes_tools.get_latest_snapshot")
def test_pit_rejoin_driver_not_found(mock_snapshot, mock_exists):
    mock_exists.return_value = True
    mock_snapshot.return_value = SAMPLE_SNAPSHOT

    response = client.post("/tools/project_pit_rejoin", json={
        "session_id": "test_session",
        "driver_code": "RIC",
    })
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "driver_not_found"


@patch("app.deps.session_exists")
@patch("app.services.snapshot_service.get_pace_history")
@patch("app.api.routes_tools.get_latest_snapshot")
def test_recommend_strategy_returns_deterministic_payload(mock_snapshot, mock_pace, mock_exists):
    mock_exists.return_value = True
    mock_snapshot.return_value = SAMPLE_SNAPSHOT
    mock_pace.side_effect = lambda session_id, driver_code: PACE_HISTORY.get(driver_code, [])

    response = client.post("/tools/recommend_strategy", json={
        "session_id": "test_session",
        "driver_code": "NOR",
    })
    assert response.status_code == 200
    data = response.json()

    assert data["recommended_action"] in {
        "pit_now", "stay_out", "cover_undercut", "extend_stint", "insufficient_data",
    }
    assert data["source"] == "replay"
    assert data["mode"] == "replay"
    assert data["snapshot_ingest_ts_utc"] == "2026-02-28T06:00:01Z"
    assert data["source_ts_utc"] == "2024-03-24T05:22:10Z"
    assert data["supporting_evidence"]["focus_driver"]["driver_code"] == "NOR"
    assert "pit_rejoin" in data["supporting_evidence"]
