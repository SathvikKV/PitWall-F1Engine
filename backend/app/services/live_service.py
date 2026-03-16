"""
Live ingestion service — mirrors replay_service.py in structure.

Polls OpenF1 every poll_interval_s, assembles a RaceSnapshot, and writes
it to Redis using the same keys as replay so all tool endpoints work unchanged.
"""

import asyncio
import logging
from typing import Any, Dict

import httpx

from app.adapters.openf1_snapshot_builder import build_snapshot
from app.adapters.openf1_client import fetch_session_info
from app.config.settings import settings
from app.services.redis_client import get_json, set_json
from app.services.session_service import create_session, session_exists
from app.services.snapshot_service import save_snapshot, update_pace_history_from_snapshot
from app.utils.time_utils import current_time_utc

logger = logging.getLogger(__name__)

_active_live: Dict[str, asyncio.Task] = {}


def _state_key(session_id: str) -> str:
    return f"live_state:{session_id}"


def get_live_status(session_id: str) -> Dict[str, Any]:
    state = get_json(_state_key(session_id))
    if not state:
        return {"running": False, "status": "not_started"}
    return state


def stop_live(session_id: str) -> bool:
    task = _active_live.get(session_id)
    if task and not task.done():
        task.cancel()
        del _active_live[session_id]
        state = get_json(_state_key(session_id)) or {}
        state["running"] = False
        state["status"] = "stopped"
        set_json(_state_key(session_id), state)
        return True
    return False


async def _live_worker(
    session_id: str,
    openf1_session_key: str,
    poll_interval_s: float,
) -> None:
    if not session_exists(session_id):
        create_session(session_id)

    state: Dict[str, Any] = {
        "running": True,
        "status": "resolving_session",
        "session_id": session_id,
        "openf1_session_key": openf1_session_key,
        "poll_interval_s": poll_interval_s,
        "session_type": None,
        "session_name": None,
        "ticks": 0,
        "errors": 0,
        "last_ingest_ts": None,
    }
    set_json(_state_key(session_id), state)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # ── Resolve session metadata once at startup ───────────────────────
        session_info = await fetch_session_info(openf1_session_key, client)
        session_type: str = session_info.get("session_type") or "Unknown"
        session_name: str = session_info.get("session_name") or openf1_session_key

        state["session_type"] = session_type
        state["session_name"] = session_name
        state["status"] = "polling"

        _RACE_SESSIONS = {"Race", "Sprint"}
        if session_type not in _RACE_SESSIONS:
            logger.warning(
                "Live session '%s' (type=%s) is not a race — strategy tools "
                "(recommend_strategy, estimate_undercut, project_pit_rejoin) "
                "will return not_applicable for this session.",
                session_name, session_type,
            )

        logger.info(
            "Live worker started: session=%s of1key=%s type=%s poll=%.1fs",
            session_id, openf1_session_key, session_type, poll_interval_s,
        )
        set_json(_state_key(session_id), state)

        # ── Poll loop ──────────────────────────────────────────────────────
        tick = 0
        while True:
            try:
                snapshot = await build_snapshot(
                    session_id, openf1_session_key, client, session_type=session_type
                )
                if snapshot:
                    snap_dict = snapshot.model_dump()
                    save_snapshot(session_id, snap_dict, ttl_s=30)
                    update_pace_history_from_snapshot(session_id, snap_dict)
                    state["ticks"] += 1
                    state["last_ingest_ts"] = current_time_utc()
                    state["last_lap"] = snapshot.lap

                    # Re-resolve session type every 60 ticks (~4 min)
                    # so that if we started before the session changed
                    # (e.g. quali→race), we pick up the new type.
                    tick += 1
                    if tick % 60 == 0 and openf1_session_key == "latest":
                        info = await fetch_session_info(openf1_session_key, client)
                        new_type = info.get("session_type") or session_type
                        if new_type != session_type:
                            logger.info(
                                "Session type changed: %s → %s",
                                session_type, new_type,
                            )
                            session_type = new_type
                            session_name = info.get("session_name") or session_name
                            state["session_type"] = session_type
                            state["session_name"] = session_name

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                state["errors"] += 1
                state["last_error"] = str(exc)
                logger.error("Live worker error (session=%s): %s", session_id, exc)

            set_json(_state_key(session_id), state)
            await asyncio.sleep(poll_interval_s)


async def _live_worker_wrapper(
    session_id: str,
    openf1_session_key: str,
    poll_interval_s: float,
) -> None:
    try:
        await _live_worker(session_id, openf1_session_key, poll_interval_s)
    except asyncio.CancelledError:
        logger.info("Live worker cancelled for session %s", session_id)
    except Exception as exc:
        logger.error("Live worker fatal error for session %s: %s", session_id, exc)
        state = get_json(_state_key(session_id)) or {}
        state["running"] = False
        state["status"] = "error"
        state["last_error"] = str(exc)
        set_json(_state_key(session_id), state)
    finally:
        if session_id in _active_live:
            del _active_live[session_id]


def start_live(
    session_id: str,
    openf1_session_key: str = "latest",
    poll_interval_s: float | None = None,
) -> bool:
    if session_id in _active_live and not _active_live[session_id].done():
        return False  # already running

    interval = poll_interval_s if poll_interval_s is not None else settings.OPENF1_POLL_INTERVAL_S
    task = asyncio.create_task(
        _live_worker_wrapper(session_id, openf1_session_key, interval)
    )
    _active_live[session_id] = task
    return True
