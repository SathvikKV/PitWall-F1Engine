import json
from typing import Optional, List

from app.services.redis_client import get_json, set_json, redis_client

PACE_HIST_MAX_K = 6

def get_snapshot_key(session_id: str) -> str:
    return f"race_snapshot:{session_id}"

def get_pace_hist_key(session_id: str, driver_code: str) -> str:
    return f"pace_hist:{session_id}:{driver_code}"

def get_latest_snapshot(session_id: str) -> Optional[dict]:
    """Retrieve the latest race snapshot from Redis."""
    key = get_snapshot_key(session_id)
    return get_json(key)

def save_snapshot(session_id: str, snapshot_data: dict, ttl_s: int = 10) -> None:
    """Save a race snapshot to Redis with an optional TTL."""
    key = get_snapshot_key(session_id)
    set_json(key, snapshot_data, ttl_s)

def get_pace_history(session_id: str, driver_code: str) -> List[float]:
    """Return the rolling pace history list for a driver."""
    key = get_pace_hist_key(session_id, driver_code)
    raw = redis_client.get(key)
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []
    return []

def append_pace(session_id: str, driver_code: str, lap_time: float) -> None:
    """Append a lap time to the rolling pace history, capped at K entries."""
    hist = get_pace_history(session_id, driver_code)
    hist.append(lap_time)
    if len(hist) > PACE_HIST_MAX_K:
        hist = hist[-PACE_HIST_MAX_K:]
    key = get_pace_hist_key(session_id, driver_code)
    redis_client.set(key, json.dumps(hist))

def update_pace_history_from_snapshot(session_id: str, snapshot_data: dict) -> None:
    """Extract last_lap_time from each driver in the snapshot and append to Redis."""
    drivers = snapshot_data.get("drivers", [])
    for d in drivers:
        code = d.get("driver_code")
        lap_time = d.get("last_lap_time")
        if code and lap_time is not None:
            append_pace(session_id, code, lap_time)
