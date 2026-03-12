import asyncio
import json
import logging
from typing import Optional, Dict, Any

from app.services.redis_client import redis_client, get_json, set_json
from app.services.snapshot_service import save_snapshot, update_pace_history_from_snapshot
from app.services.session_service import session_exists, create_session
from app.utils.time_utils import current_time_utc

logger = logging.getLogger(__name__)

# In-memory dictionary to hold running task handles
_active_replays: Dict[str, asyncio.Task] = {}

def get_replay_state_key(session_id: str) -> str:
    return f"replay_state:{session_id}"

def get_replay_status(session_id: str) -> Dict[str, Any]:
    state = get_json(get_replay_state_key(session_id))
    if not state:
        return {"running": False, "status": "not_started"}
    return state

def stop_replay(session_id: str) -> bool:
    """Stops an active replay if running."""
    task = _active_replays.get(session_id)
    if task and not task.done():
        task.cancel()
        del _active_replays[session_id]
        
        state = get_json(get_replay_state_key(session_id)) or {}
        state["running"] = False
        set_json(get_replay_state_key(session_id), state)
        return True
    return False

async def _replay_worker(session_id: str, ndjson_path: str, tick_ms: int, loop_replay: bool):
    """Background task to stream NDJSON to Redis."""
    try:
        if not session_exists(session_id):
            create_session(session_id)
            
        with open(ndjson_path, 'r') as f:
            lines = f.readlines()
            
        if not lines:
            logger.error(f"NDJSON file empty: {ndjson_path}")
            return

        idx = 0
        state = {
            "running": True, 
            "idx": idx, 
            "ndjson_path": ndjson_path, 
            "tick_ms": tick_ms,
            "total_snapshots": len(lines)
        }
        set_json(get_replay_state_key(session_id), state)

        while idx < len(lines):
            try:
                snapshot_data = json.loads(lines[idx])
                
                # Preserve the original dataset timestamp as source
                snapshot_data["source_ts_utc"] = snapshot_data.get("timestamp_utc", "")
                # Overwrite timestamp with actual simulated current time so it appears live
                snapshot_data["timestamp_utc"] = current_time_utc()
                snapshot_data["ingest_ts_utc"] = snapshot_data["timestamp_utc"]
                snapshot_data["mode"] = "replay"
                
                # Write to Redis TTL 10 seconds
                save_snapshot(session_id, snapshot_data, ttl_s=10)
                
                # Update rolling pace history for each driver
                update_pace_history_from_snapshot(session_id, snapshot_data)
                
                # Update State
                state["idx"] = idx
                state["last_written_ts"] = snapshot_data["timestamp_utc"]
                set_json(get_replay_state_key(session_id), state)
                
                idx += 1
                
                if loop_replay and idx >= len(lines):
                    idx = 0 # loop back to start
                
                await asyncio.sleep(tick_ms / 1000.0)
                
            except json.JSONDecodeError:
                logger.error(f"Failed to decode line {idx} in {ndjson_path}")
                idx += 1
                continue
                
        # Replay finished
        state["running"] = False
        state["status"] = "finished"
        set_json(get_replay_state_key(session_id), state)
        
    except asyncio.CancelledError:
        logger.info(f"Replay worker cancelled for session {session_id}")
    except Exception as e:
        logger.error(f"Replay worker error for {session_id}: {e}")
        state = get_json(get_replay_state_key(session_id)) or {}
        state["running"] = False
        state["error"] = str(e)
        set_json(get_replay_state_key(session_id), state)
    finally:
        if session_id in _active_replays:
            del _active_replays[session_id]

def start_replay(session_id: str, ndjson_path: str, tick_ms: int = 1000, loop: bool = False) -> bool:
    """Starts the replay worker in the background."""
    if session_id in _active_replays and not _active_replays[session_id].done():
        return False # Already running
        
    task = asyncio.create_task(_replay_worker(session_id, ndjson_path, tick_ms, loop))
    _active_replays[session_id] = task
    return True
