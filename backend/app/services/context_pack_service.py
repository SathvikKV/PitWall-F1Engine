"""
Context pack service — builds query-type-specific JSON bundles that give the
LLM exactly the data it needs to answer a question, and nothing more.
"""

from typing import Any, Dict, List, Optional

from app.services.snapshot_service import get_latest_snapshot, get_pace_history
from app.config.pit_loss_config import DEFAULT_PIT_LOSS_S
from app.config.tire_config import NEW_TIRE_DELTA_S_PER_LAP
from statistics import median


def _race_ctx(snap: dict) -> Dict[str, Any]:
    return {
        "lap": snap.get("lap"),
        "track_status": snap.get("track_status"),
        "timestamp_utc": snap.get("timestamp_utc"),
    }


def _driver_state(drivers: List[dict], code: str) -> Optional[Dict[str, Any]]:
    for d in drivers:
        if d.get("driver_code") == code:
            return d
    return None


def _driver_window(drivers: List[dict], code: str, radius: int = 3) -> List[Dict[str, Any]]:
    """Return a ±radius window of drivers around the target, sorted by position."""
    with_pos = [d for d in drivers if d.get("position") is not None]
    with_pos.sort(key=lambda d: d["position"])
    idx = None
    for i, d in enumerate(with_pos):
        if d.get("driver_code") == code:
            idx = i
            break
    if idx is None:
        return []
    lo = max(0, idx - radius)
    hi = min(len(with_pos), idx + radius + 1)
    return with_pos[lo:hi]


def _pace_median(hist: List[float], n: int = 3) -> Optional[float]:
    if len(hist) < n:
        return None
    return round(median(hist[-n:]), 3)


# ── Pack builders ─────────────────────────────────────────────────────────

def _pack_pit_rejoin(snap: dict, drivers_arg: List[str], session_id: str) -> Dict[str, Any]:
    drivers = snap.get("drivers", [])
    target_code = drivers_arg[0] if drivers_arg else None
    target = _driver_state(drivers, target_code) if target_code else None
    window = _driver_window(drivers, target_code, 3) if target_code else []
    return {
        "query_type": "pit_rejoin",
        "race_context": _race_ctx(snap),
        "target_driver": target,
        "position_window": window,
        "pit_loss_s": DEFAULT_PIT_LOSS_S,
    }


def _pack_undercut(snap: dict, drivers_arg: List[str], session_id: str, horizon: int) -> Dict[str, Any]:
    drivers = snap.get("drivers", [])
    attacker_code = drivers_arg[0] if len(drivers_arg) > 0 else None
    defender_code = drivers_arg[1] if len(drivers_arg) > 1 else None

    att_state = _driver_state(drivers, attacker_code) if attacker_code else None
    def_state = _driver_state(drivers, defender_code) if defender_code else None

    att_hist = get_pace_history(session_id, attacker_code) if attacker_code else []
    def_hist = get_pace_history(session_id, defender_code) if defender_code else []

    return {
        "query_type": "undercut",
        "race_context": _race_ctx(snap),
        "attacker": att_state,
        "defender": def_state,
        "attacker_pace_median_s": _pace_median(att_hist),
        "defender_pace_median_s": _pace_median(def_hist),
        "horizon_laps": horizon,
        "pit_loss_s": DEFAULT_PIT_LOSS_S,
        "new_tire_delta_s_per_lap": NEW_TIRE_DELTA_S_PER_LAP,
    }


def _pack_strategy(snap: dict, drivers_arg: List[str], session_id: str) -> Dict[str, Any]:
    drivers = snap.get("drivers", [])
    focus_code = drivers_arg[0] if drivers_arg else None
    focus = _driver_state(drivers, focus_code) if focus_code else None
    window = _driver_window(drivers, focus_code, 3) if focus_code else []
    return {
        "query_type": "strategy",
        "race_context": _race_ctx(snap),
        "focus_driver": focus,
        "battle_window": window,
    }


def _pack_explainer(snap: dict, drivers_arg: List[str], session_id: str) -> Dict[str, Any]:
    drivers = snap.get("drivers", [])
    focus_code = drivers_arg[0] if drivers_arg else None
    focus = _driver_state(drivers, focus_code) if focus_code else None
    return {
        "query_type": "explainer",
        "race_context": _race_ctx(snap),
        "focus_driver": focus,
    }


# ── Public API ────────────────────────────────────────────────────────────

def build_context_pack(
    session_id: str,
    query_type: str,
    drivers: List[str],
    horizon_laps: int = 2,
) -> Optional[Dict[str, Any]]:
    """Return a context pack dict, or ``None`` if snapshot unavailable."""
    snap = get_latest_snapshot(session_id)
    if not snap:
        return None

    builders = {
        "pit_rejoin": lambda: _pack_pit_rejoin(snap, drivers, session_id),
        "undercut": lambda: _pack_undercut(snap, drivers, session_id, horizon_laps),
        "strategy": lambda: _pack_strategy(snap, drivers, session_id),
        "explainer": lambda: _pack_explainer(snap, drivers, session_id),
    }

    builder = builders.get(query_type)
    if not builder:
        return {"error": "unknown_query_type", "valid": list(builders.keys())}

    return builder()
