"""
Deterministic pit rejoin projection model.

Given the current race snapshot and a target driver, projects where
the driver would rejoin after a pit stop by adding pit_loss_s to
their current gap_to_leader and comparing against other drivers.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from app.models.snapshot_model import RaceSnapshot, DriverState
from app.utils.time_utils import current_time_utc


def _parse_snapshot_age_s(timestamp_utc: str) -> float:
    """Return seconds elapsed since the snapshot timestamp."""
    try:
        snap_dt = datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - snap_dt).total_seconds()
    except (ValueError, TypeError):
        return float("inf")  # Treat unparseable timestamps as stale


def project_pit_rejoin(
    snapshot: RaceSnapshot,
    driver_code: str,
    pit_loss_s: float,
) -> Dict[str, Any]:
    """
    Project where *driver_code* would rejoin the track after a pit stop.

    Algorithm (deterministic, no randomness):
      1. Find the target driver in the snapshot.
      2. Compute projected_gap = driver.gap_to_leader + pit_loss_s.
      3. Build a sorted list of all *other* drivers by gap_to_leader.
      4. Insert the pitting driver into the correct slot.
      5. Derive projected_position, gap_ahead_s, gap_behind_s.

    Returns a dict matching the ProjectPitRejoinResponse schema.

    Raises ValueError if the driver is not found in the snapshot.
    """

    # --- 1. Find the target driver ----------------------------------------
    target: Optional[DriverState] = None
    for d in snapshot.drivers:
        if d.driver_code == driver_code:
            target = d
            break

    if target is None:
        raise ValueError(f"Driver {driver_code} not found in snapshot")

    # --- 2. Compute projected gap -----------------------------------------
    current_gap = target.gap_to_leader if target.gap_to_leader is not None else 0.0
    projected_gap = current_gap + pit_loss_s

    # --- 3. Gather other drivers sorted by gap_to_leader ------------------
    others = [
        d for d in snapshot.drivers
        if d.driver_code != driver_code and d.gap_to_leader is not None
    ]
    others.sort(key=lambda d: d.gap_to_leader)  # type: ignore[arg-type]

    # --- 4. Find insertion point ------------------------------------------
    # We want the first index where the driver in `others` has a gap
    # greater than or equal to `projected_gap`.  Everything before that
    # index has a smaller gap (i.e. is ahead on track).
    insert_idx = len(others)  # default: behind everyone
    for i, d in enumerate(others):
        if d.gap_to_leader is not None and projected_gap <= d.gap_to_leader:
            insert_idx = i
            break

    # projected_position is 1-indexed (insert_idx accounts for 0-indexed list
    # of *other* drivers, so +1 converts to race position)
    projected_position = insert_idx + 1

    # --- 5. Compute gap_ahead / gap_behind --------------------------------
    gap_ahead_s: Optional[float] = None
    gap_behind_s: Optional[float] = None

    if insert_idx > 0:
        driver_ahead = others[insert_idx - 1]
        gap_ahead_s = round(projected_gap - driver_ahead.gap_to_leader, 3)  # type: ignore[operator]

    if insert_idx < len(others):
        driver_behind = others[insert_idx]
        gap_behind_s = round(driver_behind.gap_to_leader - projected_gap, 3)  # type: ignore[operator]

    # --- 6. Confidence ----------------------------------------------------
    age_s = _parse_snapshot_age_s(snapshot.timestamp_utc)
    confidence = "low" if age_s > 10 else "medium"

    return {
        "projected_position": projected_position,
        "gap_ahead_s": gap_ahead_s,
        "gap_behind_s": gap_behind_s,
        "assumptions": {
            "pit_lane_loss_s": pit_loss_s,
            "traffic_loss_s": 0.0,
        },
        "confidence": confidence,
        "timestamp_utc": snapshot.timestamp_utc,
        "source": "replay",
    }
