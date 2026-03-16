"""Admin routes for OpenF1 live ingestion: start, stop, status, session list."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.services.live_service import start_live, stop_live, get_live_status
from app.adapters.openf1_client import fetch_sessions
from app.utils.time_utils import current_time_utc

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
    
    try:
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

