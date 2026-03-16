"""Unit tests for the OpenF1 snapshot builder using mocked API payloads."""

from app.adapters.openf1_snapshot_builder import build_snapshot, _update_driver_cache
import asyncio
import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

INTERVALS = [
    {"driver_number": 4, "gap_to_leader": None, "interval": None, "date": "2024-06-02T14:30:00Z"},
    {"driver_number": 55, "gap_to_leader": 2.5, "interval": 2.5, "date": "2024-06-02T14:30:00Z"},
    {"driver_number": 44, "gap_to_leader": 5.1, "interval": 2.6, "date": "2024-06-02T14:30:00Z"},
]

STINTS = [
    {"driver_number": 4, "compound": "MEDIUM", "lap_start": 1, "lap_end": 15, "tyre_age_at_start": 0, "stint_number": 1},
    {"driver_number": 55, "compound": "HARD", "lap_start": 1, "lap_end": 15, "tyre_age_at_start": 0, "stint_number": 1},
    {"driver_number": 44, "compound": "SOFT", "lap_start": 5, "lap_end": None, "tyre_age_at_start": 2, "stint_number": 2},
]

LAPS = [
    {"driver_number": 4, "lap_number": 15, "lap_duration": 90.2},
    {"driver_number": 55, "lap_number": 15, "lap_duration": 90.8},
    {"driver_number": 44, "lap_number": 14, "lap_duration": 91.1},
]

RACE_CONTROL_CLEAN = [
    {"category": "Flag", "flag": "GREEN", "message": "GREEN FLAG", "date": "2024-06-02T14:00:00Z"},
]

RACE_CONTROL_SC = [
    {"category": "SafetyCar", "flag": "YELLOW", "message": "SAFETY CAR DEPLOYED", "date": "2024-06-02T14:28:00Z"},
]

RACE_CONTROL_VSC = [
    {"category": "VirtualSafetyCar", "flag": "YELLOW", "message": "VIRTUAL SAFETY CAR DEPLOYED", "date": "2024-06-02T14:28:00Z"},
]

DRIVERS = [
    {"driver_number": 4, "name_acronym": "NOR"},
    {"driver_number": 55, "name_acronym": "SAI"},
    {"driver_number": 44, "name_acronym": "HAM"},
]


class _FakeClient:
    """Minimal mock so build_snapshot doesn't need a real httpx client."""
    pass


# Patch the fetchers so tests don't make network calls
import unittest.mock as mock


import itertools
_key_counter = itertools.count(1)

def _fresh_key():
    return f"test_{next(_key_counter)}"


async def _make_snapshot(intervals=None, stints=None, laps=None, rc=None, session_key=None):
    if session_key is None:
        session_key = _fresh_key()
    # Prime the driver cache for this key
    _update_driver_cache(session_key, DRIVERS)

    with (
        mock.patch("app.adapters.openf1_snapshot_builder.fetch_intervals", return_value=intervals if intervals is not None else INTERVALS),
        mock.patch("app.adapters.openf1_snapshot_builder.fetch_stints", return_value=stints or STINTS),
        mock.patch("app.adapters.openf1_snapshot_builder.fetch_laps", return_value=laps or LAPS),
        mock.patch("app.adapters.openf1_snapshot_builder.fetch_race_control", return_value=rc or RACE_CONTROL_CLEAN),
    ):
        return await build_snapshot("pitwall_test", session_key, _FakeClient())


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_snapshot_has_correct_drivers():
    snap = asyncio.run(_make_snapshot())
    assert snap is not None
    codes = {d.driver_code for d in snap.drivers}
    assert "NOR" in codes and "SAI" in codes and "HAM" in codes


def test_leader_is_position_1():
    snap = asyncio.run(_make_snapshot())
    assert snap is not None
    pos1 = next(d for d in snap.drivers if d.position == 1)
    # Driver 4 (NOR) has gap_to_leader=None → should be leader
    assert pos1.driver_code == "NOR"
    assert pos1.gap_to_leader == 0.0


def test_gap_ahead_matches_interval():
    snap = asyncio.run(_make_snapshot())
    assert snap is not None
    sai = next(d for d in snap.drivers if d.driver_code == "SAI")
    assert sai.gap_ahead == 2.5


def test_gap_behind_populated():
    snap = asyncio.run(_make_snapshot())
    assert snap is not None
    nor = next(d for d in snap.drivers if d.driver_code == "NOR")
    # NOR is P1; car behind (SAI) has gap_ahead=2.5, so NOR.gap_behind should be 2.5
    assert nor.gap_behind == 2.5


def test_tire_compound_mapped():
    snap = asyncio.run(_make_snapshot())
    assert snap is not None
    nor = next(d for d in snap.drivers if d.driver_code == "NOR")
    assert nor.tire is not None
    assert nor.tire.compound == "MEDIUM"


def test_last_lap_time_mapped():
    snap = asyncio.run(_make_snapshot())
    assert snap is not None
    nor = next(d for d in snap.drivers if d.driver_code == "NOR")
    assert nor.last_lap_time == 90.2


def test_mode_is_live():
    snap = asyncio.run(_make_snapshot())
    assert snap is not None
    assert snap.mode == "live"


def test_lap_number_from_laps():
    snap = asyncio.run(_make_snapshot())
    assert snap is not None
    assert snap.lap == 15  # max(15, 15, 14)


def test_green_track_status():
    snap = asyncio.run(_make_snapshot(rc=RACE_CONTROL_CLEAN))
    assert snap is not None
    assert snap.track_status.sc is False
    assert snap.track_status.vsc is False


def test_safety_car_detected():
    snap = asyncio.run(_make_snapshot(rc=RACE_CONTROL_SC))
    assert snap is not None
    assert snap.track_status.sc is True


def test_vsc_detected():
    snap = asyncio.run(_make_snapshot(rc=RACE_CONTROL_VSC))
    assert snap is not None
    assert snap.track_status.vsc is True


def test_empty_intervals_returns_none():
    snap = asyncio.run(_make_snapshot(intervals=[]))
    assert snap is None
