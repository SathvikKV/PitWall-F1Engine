"""Admin routes for OpenF1 live ingestion: start, stop, status, session list."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.services.live_service import start_live, stop_live, get_live_status
from app.adapters.openf1_client import fetch_sessions
from app.utils.time_utils import current_time_utc

import httpx

TRACK_CACHE = {}

async def _fetch_track_layout(f1_session_key: str, client: httpx.AsyncClient) -> list:
    """Fetch exactly 1 lap of driver 1 to use as a track layout spline."""
    try:
        if f1_session_key == "latest": return []
        
        # Get start and end of Lap 2
        laps_url = f"https://api.openf1.org/v1/laps?session_key={f1_session_key}&driver_number=1&lap_number=2"
        resp = await client.get(laps_url, timeout=10.0)
        if resp.status_code != 200 or not resp.json():
            return []
            
        lap_data = resp.json()[0]
        date_start = lap_data.get("date_start")
        duration = lap_data.get("lap_duration")
        if not date_start or not duration: return []
        
        from datetime import datetime, timedelta
        start_dt = datetime.fromisoformat(date_start.replace('Z', '+00:00'))
        end_dt = start_dt + timedelta(seconds=duration)
        date_st = start_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')
        date_en = end_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')
        
        # Fetch high freq location data during that specific 90s window
        loc_url = f"https://api.openf1.org/v1/location?session_key={f1_session_key}&driver_number=1&date>={date_st}&date<={date_en}"
        loc_resp = await client.get(loc_url, timeout=10.0)
        if loc_resp.status_code == 200:
            return [{"x": r.get("x", 0), "y": r.get("y", 0)} for r in loc_resp.json()]
    except Exception as e:
        print(f"Failed to fetch track layout: {e}")
    return []

router = APIRouter(prefix="/admin/live", tags=["admin-live"])


class StartLiveRequest(BaseModel):
    session_id: str
    openf1_session_key: str = "latest"
    poll_interval_s: Optional[float] = None


class StopLiveRequest(BaseModel):
    session_id: str


@router.post("/start")
async def api_start_live(req: StartLiveRequest):
    success = start_live(req.session_id, req.openf1_session_key, req.poll_interval_s)
    return {
        "status": "started" if success else "already_running",
        "session_id": req.session_id,
        "openf1_session_key": req.openf1_session_key,
        "timestamp_utc": current_time_utc(),
    }


@router.post("/stop")
async def api_stop_live(req: StopLiveRequest):
    success = stop_live(req.session_id)
    return {
        "status": "stopped" if success else "not_running",
        "session_id": req.session_id,
        "timestamp_utc": current_time_utc(),
    }


@router.get("/status")
async def api_live_status(session_id: str):
    return get_live_status(session_id)


@router.get("/sessions")
async def api_live_sessions(session_key: str = "latest"):
    """Return OpenF1 session metadata for discovery."""
    try:
        sessions = await fetch_sessions(session_key)
        return {"sessions": sessions, "timestamp_utc": current_time_utc()}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenF1 fetch failed: {exc}",
        )


@router.get("/locations")
async def api_live_locations(session_key: str = "latest"):
    """Return the most recent driver (x, y) coordinates for mapping."""
    import httpx
    from app.adapters.openf1_client import fetch_location
    from app.services.snapshot_service import get_latest_snapshot
    
    try:
        # 1. If it's a local replay session, fetch from the Redis snapshot
        snap = get_latest_snapshot(session_key)
        if snap and "drivers" in snap:
            import math
            from datetime import datetime, timezone
            from app.services.replay_service import get_replay_status
            from app.utils.time_utils import current_time_utc
            
            # Interpolate based on time since snapshot
            snapshot_ts_utc_str = snap.get("timestamp_utc", "")
            try:
                snap_dt = datetime.fromisoformat(snapshot_ts_utc_str.replace('Z', '+00:00'))
                elapsed_s = (datetime.now(timezone.utc) - snap_dt).total_seconds()
            except Exception:
                elapsed_s = 0

            # Find leader's lap time
            lap_time = 90.0
            for d in snap["drivers"]:
                if d.get("position") == 1 and d.get("last_lap_time"):
                    lap_time = float(d["last_lap_time"])
                    break
                    
            status = get_replay_status(session_key)
            speed_mult = status.get("speed_multiplier", 1.0)
            sim_elapsed_s = elapsed_s * speed_mult
            
            center_x, center_y = 5000, 5000
            radius_x, radius_y = 4000, 2000
            
            # Determine actual OpenF1 session key if playing local replay
            path = status.get("ndjson_path", "")
            f1_session_key = "latest"
            if any(k in session_key or k in path for k in ["aus_2024", "aus_2025"]):
                f1_session_key = "9488"
            elif any(k in session_key or k in path for k in ["china_2024", "china_2025"]):
                f1_session_key = "9496"
            
            # Fetch and cache track outline
            if f1_session_key not in TRACK_CACHE and f1_session_key != "latest":
                async with httpx.AsyncClient() as client:
                    TRACK_CACHE[f1_session_key] = await _fetch_track_layout(f1_session_key, client)
                    
            track_points = TRACK_CACHE.get(f1_session_key, [])
            
            driver_positions = []
            baseline_progress = snap.get("leader_lap_progress_s", 0.0)
            
            for d in snap["drivers"]:
                driver_num = d.get("driver_number") or hash(d.get("driver_code", "")) % 100
                gap = d.get("gap_to_leader") or 0.0
                if d.get("position") == 1:
                    gap = 0.0
                
                # Baseline (from snapshot) + Time since snapshot - Gap
                track_pos_s = baseline_progress + sim_elapsed_s - gap
                angle = (track_pos_s % lap_time) / lap_time * 2 * math.pi
                
                if track_points:
                    progress = (track_pos_s % lap_time) / lap_time
                    idx = int(progress * len(track_points))
                    idx = min(idx, len(track_points) - 1)
                    x = track_points[idx]["x"]
                    y = track_points[idx]["y"]
                else:
                    # Plot onto virtual oval track fallback
                    x = center_x + radius_x * math.sin(angle)
                    y = center_y - radius_y * math.cos(angle)
                
                driver_positions.append({
                    "driver_number": driver_num,
                    "driver_code": d.get("driver_code", "UNK"),
                    "x": x,
                    "y": y,
                    "z": 0,
                    "date": current_time_utc()
                })
            
            if len(driver_positions) > 0:
                return {"locations": driver_positions, "timestamp_utc": current_time_utc()}
        
        # 2. Fall back to OpenF1 API
        async with httpx.AsyncClient(timeout=10.0) as client:
            locations = await fetch_location(session_key, client)
        
        # The OpenF1 '/location' endpoint returns a large dataset.
        # We process it to get the *latest* coordinate per driver.
        latest_by_driver = {}
        for record in locations:
            driver_num = record.get("driver_number")
            if driver_num is None:
                continue
            
            # Use 'date' to find the most recent record
            record_date = record.get("date", "")
            if driver_num not in latest_by_driver:
                latest_by_driver[driver_num] = record
            else:
                if record_date > latest_by_driver[driver_num].get("date", ""):
                    latest_by_driver[driver_num] = record
                    
        # Filter down to the exact data the map component needs
        driver_positions = []
        for driver_num, record in latest_by_driver.items():
            driver_positions.append({
                "driver_number": driver_num,
                "x": record.get("x", 0),
                "y": record.get("y", 0),
                "z": record.get("z", 0),
                "date": record.get("date")
            })
            
        return {"locations": driver_positions, "timestamp_utc": current_time_utc()}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenF1 location fetch failed: {exc}",
        )

@router.get("/track-layout")
async def api_track_layout(session_key: str = "latest"):
    """Returns an array of X,Y points mapping the physical track outline."""
    from app.services.replay_service import get_replay_status
    status = get_replay_status(session_key)
    path = status.get("ndjson_path", "")
    
    f1_session_key = "latest"
    s_key_lower = session_key.lower()
    path_lower = path.lower()
    
    if "aus" in s_key_lower or "aus" in path_lower:
        f1_session_key = "9488"
    elif "china" in s_key_lower or "china" in path_lower:
        f1_session_key = "9496"
        
    if f1_session_key in TRACK_CACHE:
        return {"layout": TRACK_CACHE[f1_session_key]}
        
    async with httpx.AsyncClient() as client:
        pts = await _fetch_track_layout(f1_session_key, client)
        if pts: 
            TRACK_CACHE[f1_session_key] = pts
        return {"layout": pts}


class JumpRequest(BaseModel):
    session_id: str
    lap: int


@router.post("/jump")
async def api_jump_live(req: JumpRequest):
    """Signal the replay worker to jump to a specific lap."""
    from app.services.replay_service import jump_to_lap
    success = jump_to_lap(req.session_id, req.lap)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to jump to lap (replay not running or lap not found)")
    return {"status": "jumped", "lap": req.lap}

