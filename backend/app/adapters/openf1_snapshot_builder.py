"""
Assembles a RaceSnapshot from live OpenF1 REST API responses.

Fetches four endpoints in parallel and normalizes the data into the
same RaceSnapshot schema used by the replay pipeline.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.adapters.openf1_client import (
    fetch_drivers,
    fetch_intervals,
    fetch_laps,
    fetch_race_control,
    fetch_stints,
)
from app.models.snapshot_model import DriverState, RaceSnapshot, TireState, TrackStatus
from app.utils.time_utils import current_time_utc

logger = logging.getLogger(__name__)

# ── Driver number → acronym cache ────────────────────────────────────────────
# Built once per live session to avoid fetching drivers on every poll tick.
_driver_cache: Dict[str, Dict[int, str]] = {}  # session_key → {driver_number: acronym}


def _get_driver_acronym(session_key: str, driver_number: int) -> str:
    cache = _driver_cache.get(session_key, {})
    return cache.get(driver_number, f"D{driver_number:02d}")


def _update_driver_cache(session_key: str, drivers_raw: List[Dict[str, Any]]) -> None:
    cache: Dict[int, str] = {}
    for d in drivers_raw:
        num = d.get("driver_number")
        acronym = d.get("name_acronym")
        if num is not None and acronym:
            cache[int(num)] = str(acronym)
    _driver_cache[session_key] = cache
    logger.debug("Driver cache updated for session %s: %d drivers", session_key, len(cache))


# ── Track status helpers ──────────────────────────────────────────────────────

def _parse_track_status(race_control: List[Dict[str, Any]]) -> TrackStatus:
    """
    Derive track status from the most recent relevant race control messages.
    Messages are returned in chronological order; we scan backwards.
    """
    flag = "GREEN"
    sc = False
    vsc = False

    for msg in reversed(race_control):
        cat = (msg.get("category") or "").upper().replace(" ", "")
        msg_flag = (msg.get("flag") or "").upper()
        msg_text = (msg.get("message") or "").upper()

        # VSC must be checked BEFORE SC since VSC messages can also contain "SAFETY CAR"
        if cat == "VIRTUALSAFETYCAR" or "VIRTUAL SAFETY CAR" in msg_text:
            if "DEPLOYED" in msg_text:
                vsc = True
            break

        if cat in ("SAFETYCAR", "SAFETY_CAR") or ("SAFETY CAR" in msg_text and "VIRTUAL" not in msg_text):
            if "DEPLOYED" in msg_text or "RESUME" not in msg_text:
                sc = True
            break

        if cat == "FLAG" and msg_flag in ("GREEN", "YELLOW", "DOUBLE YELLOW", "RED", "CHEQUERED"):
            flag = msg_flag.replace("DOUBLE YELLOW", "YELLOW")
            break

    return TrackStatus(flag=flag, sc=sc, vsc=vsc)


# ── Lap number helper ─────────────────────────────────────────────────────────

def _current_lap(laps_raw: List[Dict[str, Any]]) -> Optional[int]:
    """Return the highest lap_number seen across all drivers."""
    laps = [int(r["lap_number"]) for r in laps_raw if r.get("lap_number") is not None]
    return max(laps) if laps else None


# ── Tire state per driver ─────────────────────────────────────────────────────

def _build_tire_map(stints_raw: List[Dict[str, Any]]) -> Dict[int, TireState]:
    """
    For each driver, find the stint with the highest lap_start (= current stint).
    Returns {driver_number: TireState}.
    """
    best: Dict[int, Dict[str, Any]] = {}
    for s in stints_raw:
        num = s.get("driver_number")
        if num is None:
            continue
        num = int(num)
        lap_start = s.get("lap_start") or 0
        if num not in best or lap_start > (best[num].get("lap_start") or 0):
            best[num] = s

    tire_map: Dict[int, TireState] = {}
    for num, stint in best.items():
        compound = stint.get("compound") or None
        age_at_start = stint.get("tyre_age_at_start") or 0
        lap_start = stint.get("lap_start") or 0
        lap_end = stint.get("lap_end")
        # Rough current age = laps since this stint started + age at start
        # We can't know exact current lap from stints alone, so we use lap_end if available
        current_age = None
        if lap_end:
            current_age = int(lap_end) - int(lap_start) + int(age_at_start)
        elif lap_start:
            current_age = int(age_at_start)
        tire_map[num] = TireState(compound=compound, age=current_age)
    return tire_map


# ── Last lap time per driver ──────────────────────────────────────────────────

def _build_last_lap_map(laps_raw: List[Dict[str, Any]]) -> Dict[int, float]:
    """For each driver, find the most recent complete lap time."""
    best: Dict[int, Tuple[int, float]] = {}  # num → (lap_number, duration)
    for lap in laps_raw:
        num = lap.get("driver_number")
        lap_num = lap.get("lap_number")
        duration = lap.get("lap_duration")
        if num is None or lap_num is None or duration is None:
            continue
        num = int(num)
        lap_num = int(lap_num)
        if num not in best or lap_num > best[num][0]:
            best[num] = (lap_num, float(duration))
    return {num: t[1] for num, t in best.items()}


# ── Main builder ──────────────────────────────────────────────────────────────

async def build_snapshot(
    pitwall_session_id: str,
    openf1_session_key: str,
    client: httpx.AsyncClient,
    session_type: Optional[str] = None,
) -> Optional[RaceSnapshot]:
    """
    Fetch all required OpenF1 endpoints in parallel and assemble a RaceSnapshot.
    Returns None if intervals data is unavailable (session not yet started).
    session_type is stamped onto the snapshot if provided (e.g. "Race", "Qualifying").
    """
    import asyncio

    # Parallel fetch
    intervals_raw, stints_raw, laps_raw, rc_raw = await asyncio.gather(
        fetch_intervals(openf1_session_key, client),
        fetch_stints(openf1_session_key, client),
        fetch_laps(openf1_session_key, client),
        fetch_race_control(openf1_session_key, client),
    )

    if not intervals_raw:
        logger.warning("No interval data from OpenF1 for session %s — skipping tick.", openf1_session_key)
        return None

    # Refresh driver cache if needed
    if openf1_session_key not in _driver_cache:
        drivers_raw = await fetch_drivers(openf1_session_key, client)
        _update_driver_cache(openf1_session_key, drivers_raw)

    # Build supporting maps
    tire_map = _build_tire_map(stints_raw)
    last_lap_map = _build_last_lap_map(laps_raw)
    track_status = _parse_track_status(rc_raw)
    lap = _current_lap(laps_raw)

    # Use latest OpenF1 timestamp as source_ts
    latest_source_ts = max(
        (r.get("date", "") for r in intervals_raw if r.get("date")),
        default="",
    )

    # Build per-driver states from intervals
    # intervals endpoint returns one row per driver per update tick; take the latest per driver
    latest_by_driver: Dict[int, Dict[str, Any]] = {}
    for row in intervals_raw:
        num = row.get("driver_number")
        if num is None:
            continue
        num = int(num)
        if num not in latest_by_driver or (row.get("date") or "") > (latest_by_driver[num].get("date") or ""):
            latest_by_driver[num] = row

    # Sort by gap_to_leader to assign positions
    sorted_rows = sorted(
        latest_by_driver.values(),
        key=lambda r: (
            # Leader has gap_to_leader=None → sort key 0.0 (first)
            # Lapped cars have "+N LAP" strings → sort key 999.0 (last)
            0.0
            if r.get("gap_to_leader") is None
            else (
                float(r["gap_to_leader"])
                if isinstance(r["gap_to_leader"], (int, float))
                else 999.0
            )
        ),
    )

    drivers: List[DriverState] = []
    prev_gap: Optional[float] = None

    for pos_idx, row in enumerate(sorted_rows):
        num = int(row["driver_number"])
        acronym = _get_driver_acronym(openf1_session_key, num)

        # gap_to_leader: None for leader, float seconds or "+N LAP" string for others
        raw_gtl = row.get("gap_to_leader")
        if raw_gtl is None:
            gap_to_leader = 0.0
        elif isinstance(raw_gtl, (int, float)):
            gap_to_leader = float(raw_gtl)
        else:
            # "+1 LAP" etc — represent as large number so strategy models skip
            gap_to_leader = 999.0

        # interval = gap to car directly ahead
        raw_interval = row.get("interval")
        if raw_interval is None:
            gap_ahead = None
        elif isinstance(raw_interval, (int, float)):
            gap_ahead = float(raw_interval)
        else:
            gap_ahead = 999.0

        driver = DriverState(
            driver_code=acronym,
            position=pos_idx + 1,
            gap_to_leader=gap_to_leader,
            gap_ahead=gap_ahead,
            gap_behind=None,  # filled in second pass
            tire=tire_map.get(num),
            last_lap_time=last_lap_map.get(num),
        )
        drivers.append(driver)

    # Second pass: gap_behind
    for i in range(len(drivers) - 1):
        if drivers[i + 1].gap_ahead is not None:
            drivers[i].gap_behind = drivers[i + 1].gap_ahead

    now = current_time_utc()
    return RaceSnapshot(
        session_id=pitwall_session_id,
        timestamp_utc=now,
        lap=lap,
        track_status=track_status,
        drivers=drivers,
        mode="live",
        session_type=session_type,
        ingest_ts_utc=now,
        source_ts_utc=latest_source_ts or now,
    )
