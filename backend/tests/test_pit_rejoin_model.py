"""Unit tests for the deterministic pit rejoin model."""

import pytest
from datetime import datetime, timezone

from app.models.snapshot_model import RaceSnapshot, DriverState, TireState, TrackStatus
from app.strategy.pit_rejoin_model import project_pit_rejoin


def _ts_now() -> str:
    """Return a fresh UTC ISO timestamp so confidence stays 'medium'."""
    return datetime.now(timezone.utc).isoformat()


def _make_snapshot(drivers, ts=None):
    return RaceSnapshot(
        session_id="test",
        timestamp_utc=ts or _ts_now(),
        lap=10,
        track_status=TrackStatus(sc=False, vsc=False, flag="GREEN"),
        drivers=drivers,
    )


# ── Case 1: Simple 3-driver scenario ─────────────────────────────────────

def test_three_driver_rejoin():
    """
    VER (leader, gap 0) | NOR (gap 5.0) | LEC (gap 10.0)
    NOR pits with 21 s loss → projected gap = 26.0
    Expected rejoin: P3 (behind LEC at 10.0, ahead of nobody)
    """
    drivers = [
        DriverState(driver_code="VER", position=1, gap_to_leader=0.0),
        DriverState(driver_code="NOR", position=2, gap_to_leader=5.0),
        DriverState(driver_code="LEC", position=3, gap_to_leader=10.0),
    ]
    snap = _make_snapshot(drivers)
    result = project_pit_rejoin(snap, "NOR", pit_loss_s=21.0)

    assert result["projected_position"] == 3  # behind VER & LEC
    assert result["gap_ahead_s"] == pytest.approx(16.0, abs=0.01)  # 26 - 10
    assert result["gap_behind_s"] is None  # nobody behind
    assert result["assumptions"]["pit_lane_loss_s"] == 21.0
    assert result["confidence"] == "medium"


def test_rejoin_between_drivers():
    """
    VER 0 | NOR 5 | LEC 10 | PIA 30 | ALO 35
    NOR pits → projected gap = 5+21 = 26
    Others sorted: VER(0), LEC(10), PIA(30), ALO(35)
    26 < 30, so NOR inserts before PIA → P3 (behind VER, LEC)
    gap_ahead = 26-10 = 16, gap_behind = 30-26 = 4
    """
    drivers = [
        DriverState(driver_code="VER", position=1, gap_to_leader=0.0),
        DriverState(driver_code="NOR", position=2, gap_to_leader=5.0),
        DriverState(driver_code="LEC", position=3, gap_to_leader=10.0),
        DriverState(driver_code="PIA", position=4, gap_to_leader=30.0),
        DriverState(driver_code="ALO", position=5, gap_to_leader=35.0),
    ]
    snap = _make_snapshot(drivers)
    result = project_pit_rejoin(snap, "NOR", pit_loss_s=21.0)

    assert result["projected_position"] == 3
    assert result["gap_ahead_s"] == pytest.approx(16.0)
    assert result["gap_behind_s"] == pytest.approx(4.0)


# ── Case 2: Driver not found ─────────────────────────────────────────────

def test_driver_not_found():
    drivers = [
        DriverState(driver_code="VER", position=1, gap_to_leader=0.0),
    ]
    snap = _make_snapshot(drivers)
    with pytest.raises(ValueError, match="RIC"):
        project_pit_rejoin(snap, "RIC", pit_loss_s=21.0)


# ── Case 3: Single-driver scenario ───────────────────────────────────────

def test_single_driver():
    """Only one driver — rejoin is P1 with no gaps."""
    drivers = [
        DriverState(driver_code="VER", position=1, gap_to_leader=0.0),
    ]
    snap = _make_snapshot(drivers)
    result = project_pit_rejoin(snap, "VER", pit_loss_s=21.0)

    assert result["projected_position"] == 1
    assert result["gap_ahead_s"] is None
    assert result["gap_behind_s"] is None


# ── Case 4: Confidence logic (stale timestamp) ───────────────────────────

def test_confidence_low_when_stale():
    """A snapshot older than 10 s should yield 'low' confidence."""
    drivers = [
        DriverState(driver_code="VER", position=1, gap_to_leader=0.0),
        DriverState(driver_code="NOR", position=2, gap_to_leader=5.0),
    ]
    old_ts = "2020-01-01T00:00:00Z"  # definitely stale
    snap = _make_snapshot(drivers, ts=old_ts)
    result = project_pit_rejoin(snap, "NOR", pit_loss_s=21.0)

    assert result["confidence"] == "low"


def test_confidence_medium_when_fresh():
    """A fresh snapshot should yield 'medium'."""
    drivers = [
        DriverState(driver_code="VER", position=1, gap_to_leader=0.0),
        DriverState(driver_code="NOR", position=2, gap_to_leader=5.0),
    ]
    snap = _make_snapshot(drivers)  # uses _ts_now()
    result = project_pit_rejoin(snap, "NOR", pit_loss_s=21.0)

    assert result["confidence"] == "medium"


# ── Edge: leader pits ────────────────────────────────────────────────────

def test_leader_pits():
    """
    VER leads (gap 0), pits → projected gap 21.
    NOR at 5, LEC at 10.
    VER rejoins behind LEC (10) → P3.
    """
    drivers = [
        DriverState(driver_code="VER", position=1, gap_to_leader=0.0),
        DriverState(driver_code="NOR", position=2, gap_to_leader=5.0),
        DriverState(driver_code="LEC", position=3, gap_to_leader=10.0),
    ]
    snap = _make_snapshot(drivers)
    result = project_pit_rejoin(snap, "VER", pit_loss_s=21.0)

    assert result["projected_position"] == 3
    assert result["gap_ahead_s"] == pytest.approx(11.0)  # 21 - 10
    assert result["gap_behind_s"] is None
