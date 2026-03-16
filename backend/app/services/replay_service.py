import asyncio
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from app.services.redis_client import redis_client, get_json, set_json
from app.services.snapshot_service import save_snapshot, update_pace_history_from_snapshot
from app.services.session_service import session_exists, create_session
from app.utils.time_utils import current_time_utc

logger = logging.getLogger(__name__)

# In-memory dictionary to hold running task handles and skip events
_active_replays: Dict[str, asyncio.Task] = {}
_replay_events: Dict[str, asyncio.Event] = {}

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

async def _replay_worker(session_id: str, ndjson_path: str, speed_multiplier: float, loop_replay: bool):
    """Background task to stream NDJSON to Redis."""
    try:
        if not session_exists(session_id):
            create_session(session_id)
            
        with open(ndjson_path, 'r') as f:
            lines = f.readlines()
            
        if not lines:
            logger.error(f"NDJSON file empty: {ndjson_path}")
            return

        # Clear existing pace history and snapshots for this session to prevent lap jumping
        try:
            keys_to_delete = redis_client.keys(f"pace_hist:{session_id}:*")
            keys_to_delete.extend(redis_client.keys(f"race_snapshot:{session_id}"))
            keys_to_delete.extend(redis_client.keys(f"replay_state:{session_id}"))
            if keys_to_delete:
                redis_client.delete(*keys_to_delete)
        except Exception as e:
            logger.warning(f"Failed to clear old session data for {session_id}: {e}")

        idx = 0
        state = {
            "running": True, 
            "idx": idx, 
            "ndjson_path": ndjson_path, 
            "speed_multiplier": speed_multiplier,
            "total_snapshots": len(lines),
            "jump_to_lap": None
        }
        set_json(get_replay_state_key(session_id), state)

        while idx < len(lines):
            try:
                # Check for jump signal
                current_state = get_json(get_replay_state_key(session_id))
                if not current_state or not current_state.get("running"):
                    return
                
                requested_lap = current_state.get("jump_to_lap")
                if requested_lap is not None:
                    # Search for the first line with this lap
                    found_idx = -1
                    for i, line in enumerate(lines):
                        try:
                            l_data = json.loads(line)
                            if l_data.get("lap") == requested_lap:
                                found_idx = i
                                break
                        except: continue
                    
                    if found_idx != -1:
                        idx = found_idx
                        state["idx"] = idx
                        state["jump_to_lap"] = None # Clear signal
                        set_json(get_replay_state_key(session_id), state)
                        logger.info(f"Jumping to lap {requested_lap} at index {idx}")
                    else:
                        state["jump_to_lap"] = None # Lap not found, clear signal
                        set_json(get_replay_state_key(session_id), state)

                snapshot_data = json.loads(lines[idx])
                
                # Preserve the original dataset timestamp as source
                snapshot_data["source_ts_utc"] = snapshot_data.get("timestamp_utc", "")
                # Overwrite timestamp with actual simulated current time so it appears live
                snapshot_data["timestamp_utc"] = current_time_utc()
                snapshot_data["ingest_ts_utc"] = snapshot_data["timestamp_utc"]
                snapshot_data["mode"] = "replay"
                snapshot_data["session_type"] = "Race"
                
                # We will write to Redis AFTER we calculate how long to sleep, so we set TTL properly
                
                # Compute sleep time for the NEXT row to maintain linear pacing based on actual lap time
                sleep_s = 1.0
                next_data = None
                if idx + 1 < len(lines):
                    try:
                        next_data = json.loads(lines[idx + 1])
                        leader = next((d for d in snapshot_data.get("drivers", []) if d.get("position") == 1), None)
                        if leader and leader.get("last_lap_time"):
                            delta_s = float(leader["last_lap_time"])
                        else:
                            delta_s = 90.0 # fallback average lap time 
                        
                        sleep_s = delta_s / speed_multiplier
                    except Exception as e:
                        logger.warning(f"Error computing sleep delta at idx {idx}: {e}")
                        sleep_s = 85.0 / speed_multiplier
                
                # Update rolling pace history BEFORE the micro-ticks so it reflects the real lap crossing
                snapshot_data["source_ts_utc"] = snapshot_data.get("timestamp_utc", "")
                update_pace_history_from_snapshot(session_id, snapshot_data)
                
                # Map next gaps for interpolation
                next_gaps = {}
                if next_data and "drivers" in next_data:
                    for d in next_data["drivers"]:
                        dc = d.get("driver_code")
                        if dc:
                            next_gaps[dc] = d.get("gap_to_leader") or 0.0

                tick_interval = 1.0 # Update every 1 real-world second
                num_ticks = max(1, int(sleep_s / tick_interval))
                
                for tick in range(num_ticks):
                    progress = tick / float(num_ticks) # 0.0 to 0.99
                    
                    interp_snap = json.loads(json.dumps(snapshot_data)) # deep copy
                    interp_snap["timestamp_utc"] = current_time_utc()
                    interp_snap["ingest_ts_utc"] = interp_snap["timestamp_utc"]
                    interp_snap["mode"] = "replay"
                    interp_snap["session_type"] = "Race"
                    
                    # Add baseline progress for the leader (seconds into lap)
                    interp_snap["leader_lap_progress_s"] = tick * tick_interval
                    
                    if next_data and progress > 0.0:
                        for d in interp_snap.get("drivers", []):
                            dc = d.get("driver_code")
                            if dc and dc in next_gaps:
                                curr_gap = d.get("gap_to_leader") or 0.0
                                next_gap = next_gaps[dc]
                                d["gap_to_leader"] = curr_gap + (next_gap - curr_gap) * progress
                        
                        # Use the interpolated lap progress if we have a leader
                        if "drivers" in interp_snap and len(interp_snap["drivers"]) > 0:
                            # Re-sort positions dynamically based on new interpolated gaps
                            drivers_list = interp_snap.get("drivers", [])
                            drivers_list.sort(key=lambda x: x.get("gap_to_leader") or 0.0)
                            for i, d in enumerate(drivers_list):
                                d["position"] = i + 1

                    # Write to Redis with a TTL long enough to survive this sleep duration
                    save_snapshot(session_id, interp_snap, ttl_s=int(tick_interval + 15))
                    
                    # Update State
                    state["idx"] = idx
                    state["last_written_ts"] = interp_snap["timestamp_utc"]
                    set_json(get_replay_state_key(session_id), state)
                    
                    # Check if stop requested
                    current_state = get_json(get_replay_state_key(session_id))
                    if not current_state or not current_state.get("running"):
                        return # Abort!
                    
                    # Execute the actual real-time delay sleep, but make it interruptible
                    event = _replay_events.get(session_id)
                    if event:
                        try:
                            await asyncio.wait_for(event.wait(), timeout=tick_interval)
                            event.clear()
                            # If we were woken up by the event, it's likely a jump request.
                            # Break out of the tick loop to check for the jump signal at the top.
                            break 
                        except asyncio.TimeoutError:
                            # Normal tick interval elapsed
                            pass
                    else:
                        await asyncio.sleep(tick_interval)
                
                idx += 1
                
                if loop_replay and idx >= len(lines):
                    idx = 0 # loop back to start
                
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
        if session_id in _replay_events:
            del _replay_events[session_id]

def start_replay(session_id: str, ndjson_path: str, speed_multiplier: float = 1.0, loop: bool = False) -> bool:
    """Starts the replay worker in the background."""
    if session_id in _active_replays and not _active_replays[session_id].done():
        return False # Already running
        
    event = asyncio.Event()
    _replay_events[session_id] = event
    task = asyncio.create_task(_replay_worker(session_id, ndjson_path, speed_multiplier, loop))
    _active_replays[session_id] = task
    return True


def jump_to_lap(session_id: str, lap: int) -> bool:
    """Sets a signal in Redis for the replay worker to jump to a specific lap."""
    state = get_json(get_replay_state_key(session_id))
    if not state or not state.get("running"):
        return False
    
    state["jump_to_lap"] = lap
    set_json(get_replay_state_key(session_id), state)
    
    # Trigger the event to wake the worker immediately
    event = _replay_events.get(session_id)
    if event:
        event.set()
        
    return True
