from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Any, Dict

from app.services.replay_service import start_replay, stop_replay, get_replay_status
from app.utils.time_utils import current_time_utc

router = APIRouter(prefix="/admin/replay", tags=["admin"])

class StartReplayRequest(BaseModel):
    session_id: str
    ndjson_path: str
    speed_multiplier: float = 1.0
    loop: bool = False

class StopReplayRequest(BaseModel):
    session_id: str

@router.post("/start")
async def api_start_replay(req: StartReplayRequest):
    import os
    if not os.path.exists(req.ndjson_path):
        raise HTTPException(status_code=400, detail=f"File not found: {req.ndjson_path}")
        
    success = start_replay(req.session_id, req.ndjson_path, req.speed_multiplier, req.loop)
    if not success:
        return {"status": "already_running", "session_id": req.session_id}
        
    return {
        "status": "started",
        "session_id": req.session_id,
        "timestamp_utc": current_time_utc()
    }

@router.post("/stop")
async def api_stop_replay(req: StopReplayRequest):
    success = stop_replay(req.session_id)
    return {
        "status": "stopped" if success else "not_running",
        "session_id": req.session_id,
        "timestamp_utc": current_time_utc()
    }

@router.get("/status")
async def api_replay_status(session_id: str):
    return get_replay_status(session_id)
