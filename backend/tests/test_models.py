import pytest
from pydantic import ValidationError
from app.models.snapshot_model import DriverState, TireState, TrackStatus, RaceSnapshot
from app.utils.time_utils import current_time_utc

def test_driver_state_valid():
    driver = DriverState(
        driver_code="VER",
        position=1,
        gap_to_leader=0.0,
        gap_ahead=0.0,
        gap_behind=1.2,
        tire=TireState(compound="MED", age=12),
        last_lap_time=80.231
    )
    assert driver.driver_code == "VER"
    assert driver.position == 1

def test_driver_state_invalid_code():
    with pytest.raises(ValidationError):
        DriverState(driver_code="ver", position=1)
    with pytest.raises(ValidationError):
        DriverState(driver_code="VERS", position=1)

def test_driver_state_unk():
    driver = DriverState(driver_code="UNK", position=20)
    assert driver.driver_code == "UNK"

def test_race_snapshot_valid():
    snapshot = RaceSnapshot(
        session_id="aus_2024_race",
        timestamp_utc=current_time_utc(),
        lap=18,
        track_status=TrackStatus(sc=False, vsc=False, flag="GREEN"),
        drivers=[
            DriverState(
                driver_code="VER",
                position=1,
                gap_to_leader=0,
                gap_behind=1.2,
                tire=TireState(compound="MED", age=12),
                last_lap_time=80.231
            )
        ]
    )
    assert snapshot.session_id == "aus_2024_race"
    assert snapshot.lap == 18
    assert snapshot.track_status.flag == "GREEN"
    assert len(snapshot.drivers) == 1
