"""Tests for the recommend_strategy deterministic model."""
from app.models.snapshot_model import (
    RaceSnapshot, DriverState, TireState, TrackStatus,
)
from app.strategy.recommend_model import recommend_strategy


def _make_snapshot(
    drivers,
    flag="GREEN",
    sc=False,
    vsc=False,
    lap=30,
    ts="2024-03-24T14:30:00Z",
    mode="replay",
    ingest_ts_utc=None,
    source_ts_utc=None,
) -> RaceSnapshot:
    return RaceSnapshot(
        session_id="test",
        timestamp_utc=ts,
        lap=lap,
        track_status=TrackStatus(flag=flag, sc=sc, vsc=vsc),
        drivers=drivers,
        mode=mode,
        ingest_ts_utc=ingest_ts_utc,
        source_ts_utc=source_ts_utc,
    )


def _driver(code, position, gap_to_leader, gap_ahead=None, gap_behind=None,
            tire_compound="MEDIUM", tire_age=10, last_lap=90.0):
    return DriverState(
        driver_code=code,
        position=position,
        gap_to_leader=gap_to_leader,
        gap_ahead=gap_ahead,
        gap_behind=gap_behind,
        tire=TireState(compound=tire_compound, age=tire_age),
        last_lap_time=last_lap,
    )


# Pace histories for testing
FAST_PACE = [89.0, 89.2, 89.1, 89.3, 89.0]
SLOW_PACE = [91.5, 91.8, 91.6, 91.7, 91.9]
MEDIUM_PACE = [90.0, 90.1, 90.2, 90.0, 90.1]


def test_safety_car_recommends_pit_now():
    drivers = [
        _driver("NOR", 1, 0.0, gap_behind=1.0),
        _driver("PIA", 2, 1.0, gap_ahead=1.0, gap_behind=2.0),
    ]
    snap = _make_snapshot(drivers, sc=True, flag="YELLOW")
    result = recommend_strategy(snap, "NOR", {})
    assert result["recommended_action"] == "pit_now"
    assert any("Safety Car" in r for r in result["reasons"])


def test_vsc_recommends_pit_now():
    drivers = [_driver("NOR", 1, 0.0)]
    snap = _make_snapshot(drivers, vsc=True)
    result = recommend_strategy(snap, "NOR", {})
    assert result["recommended_action"] == "pit_now"


def test_strong_undercut_recommends_pit_now():
    """If attacker (NOR) is much faster than defender ahead (VER), pit_now."""
    drivers = [
        _driver("VER", 1, 0.0, gap_behind=1.5),
        _driver("NOR", 2, 1.5, gap_ahead=1.5, gap_behind=1.2),
        _driver("PIA", 3, 2.7, gap_ahead=1.2),
    ]
    snap = _make_snapshot(drivers)
    # Use extreme pace difference + lower pit loss to make undercut feasible
    paces = {"NOR": FAST_PACE, "VER": SLOW_PACE, "PIA": MEDIUM_PACE}
    result = recommend_strategy(snap, "NOR", paces, pit_loss_s=5.0)
    assert result["recommended_action"] == "pit_now"
    assert "undercut_vs_ahead" in result.get("supporting_evidence", {})


def test_clear_air_recommends_extend():
    """Large gap behind, no pressure -> extend_stint."""
    drivers = [
        _driver("VER", 1, 0.0, gap_behind=2.0),
        _driver("NOR", 2, 2.0, gap_ahead=2.0, gap_behind=8.0),
        _driver("PIA", 3, 10.0, gap_ahead=8.0),
    ]
    snap = _make_snapshot(drivers)
    paces = {"NOR": MEDIUM_PACE, "VER": MEDIUM_PACE, "PIA": MEDIUM_PACE}
    result = recommend_strategy(snap, "NOR", paces)
    assert result["recommended_action"] == "extend_stint"


def test_undercut_threat_recommends_cover():
    """Car behind is faster and close -> cover_undercut."""
    drivers = [
        _driver("VER", 1, 0.0, gap_behind=1.5),
        _driver("NOR", 2, 1.5, gap_ahead=1.5, gap_behind=0.8),
        _driver("PIA", 3, 2.3, gap_ahead=0.8),
    ]
    snap = _make_snapshot(drivers)
    # PIA much faster, undercut threat is real with low pit loss
    paces = {"NOR": MEDIUM_PACE, "VER": MEDIUM_PACE, "PIA": FAST_PACE}
    result = recommend_strategy(snap, "NOR", paces, pit_loss_s=1.0)
    assert result["recommended_action"] == "cover_undercut"


def test_driver_not_found():
    drivers = [_driver("VER", 1, 0.0)]
    snap = _make_snapshot(drivers)
    result = recommend_strategy(snap, "NOR", {})
    assert result["recommended_action"] == "insufficient_data"


def test_result_has_required_fields():
    """Every result must include lap, timestamp, source, reasons."""
    drivers = [_driver("NOR", 1, 0.0, gap_behind=5.0)]
    snap = _make_snapshot(
        drivers,
        lap=42,
        ingest_ts_utc="2024-03-24T14:30:01Z",
        source_ts_utc="2024-03-24T14:29:59Z",
    )
    result = recommend_strategy(snap, "NOR", {"NOR": MEDIUM_PACE})
    assert "recommended_action" in result
    assert "reasons" in result
    assert "confidence" in result
    assert result["lap"] == 42
    assert result["timestamp_utc"] == "2024-03-24T14:30:00Z"
    assert result["source"] == "replay"
    assert result["mode"] == "replay"
    assert result["snapshot_ingest_ts_utc"] == "2024-03-24T14:30:01Z"
    assert result["source_ts_utc"] == "2024-03-24T14:29:59Z"
    assert result["supporting_evidence"]["focus_driver"]["driver_code"] == "NOR"
