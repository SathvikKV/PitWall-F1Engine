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
    "track_status": {"sc": False, "vsc": False, "flag": "GREEN"},
    "drivers": [
        {"driver_code": "VER", "position": 1, "gap_to_leader": 0.0},
        {"driver_code": "NOR", "position": 2, "gap_to_leader": 5.0},
        {"driver_code": "LEC", "position": 3, "gap_to_leader": 10.0},
        {"driver_code": "PIA", "position": 4, "gap_to_leader": 30.0},
    ],
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
