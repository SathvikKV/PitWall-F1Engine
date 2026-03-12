"""
Race brief service — builds a compact, timestamped summary of the current
race state from the Redis snapshot.  Designed to fit inside an LLM context
window without bloating token count.
"""

from typing import Any, Dict, List, Optional

from app.services.snapshot_service import get_latest_snapshot


def _build_top5(drivers: List[dict]) -> List[Dict[str, Any]]:
    """Return the top-5 drivers sorted by position."""
    with_pos = [d for d in drivers if d.get("position") is not None]
    with_pos.sort(key=lambda d: d["position"])
    top5 = []
    for d in with_pos[:5]:
        tire = d.get("tire") or {}
        top5.append({
            "position": d["position"],
            "driver_code": d["driver_code"],
            "gap_to_leader": d.get("gap_to_leader"),
            "tire_compound": tire.get("compound"),
            "tire_age": tire.get("age"),
        })
    return top5


def _build_focus(drivers: List[dict], code: str) -> Optional[Dict[str, Any]]:
    """Extract the focus-driver detail block."""
    for d in drivers:
        if d.get("driver_code") == code:
            tire = d.get("tire") or {}
            return {
                "driver_code": code,
                "position": d.get("position"),
                "gap_ahead": d.get("gap_ahead"),
                "gap_behind": d.get("gap_behind"),
                "tire_compound": tire.get("compound"),
                "tire_age": tire.get("age"),
                "last_lap_time": d.get("last_lap_time"),
            }
    return None


def build_race_brief(
    session_id: str,
    focus_driver: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Return a compact race brief dict, or ``None`` if no snapshot is available.
    """
    snap = get_latest_snapshot(session_id)
    if not snap:
        return None

    drivers = snap.get("drivers", [])
    ts = snap.get("track_status", {})

    brief: Dict[str, Any] = {
        "timestamp_utc": snap.get("timestamp_utc"),
        "lap": snap.get("lap"),
        "track_status": ts,
        "top5": _build_top5(drivers),
        "focus": None,
        "source": "replay",
        "mode": snap.get("mode", "replay"),
        "ingest_ts_utc": snap.get("ingest_ts_utc"),
    }

    if focus_driver:
        brief["focus"] = _build_focus(drivers, focus_driver)

    return brief
