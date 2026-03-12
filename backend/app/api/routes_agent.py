"""Agent API routes — tool registry, race brief, context packs, ephemeral tokens."""

import os
import datetime
import pathlib

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from app.agent.tool_registry import get_tool_registry
from app.services.race_brief_service import build_race_brief
from app.services.context_pack_service import build_context_pack
from app.deps import verify_session
from app.utils.time_utils import current_time_utc

router = APIRouter(prefix="/agent", tags=["agent"])


# ── Ephemeral Token ───────────────────────────────────────────────────────

class EphemeralTokenRequest(BaseModel):
    ttl_seconds: int = 900
    session_id: str = ""

@router.post("/ephemeral_token")
async def agent_ephemeral_token(req: EphemeralTokenRequest):
    from app.config import settings as app_settings
    api_key = app_settings.GEMINI_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GEMINI_API_KEY not configured on server",
        )
    try:
        from google import genai

        client = genai.Client(
            api_key=api_key,
            http_options={"api_version": "v1alpha"},
        )
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        ttl = min(req.ttl_seconds, 1800)  # cap at 30 min
        token = client.auth_tokens.create(
            config={
                "uses": 1,
                "expire_time": now + datetime.timedelta(seconds=ttl),
                "new_session_expire_time": now + datetime.timedelta(minutes=2),
                "http_options": {"api_version": "v1alpha"},
            }
        )
        return {
            "token": token.name,
            "expires_at_utc": (now + datetime.timedelta(seconds=ttl)).isoformat(),
            "timestamp_utc": current_time_utc(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to mint ephemeral token: {str(e)}",
        )


# ── System Prompt ─────────────────────────────────────────────────────────

@router.get("/system_prompt")
async def agent_system_prompt():
    prompt_path = pathlib.Path(__file__).resolve().parent.parent / "agent" / "prompts" / "system_prompt_v1.txt"
    if not prompt_path.exists():
        raise HTTPException(status_code=404, detail="System prompt file not found")
    return {"prompt": prompt_path.read_text(encoding="utf-8")}


# ── Tool Registry ─────────────────────────────────────────────────────────

@router.get("/tools")
async def agent_tools():
    return get_tool_registry()


# ── Race Brief ────────────────────────────────────────────────────────────

class RaceBriefRequest(BaseModel):
    session_id: str
    focus_driver: Optional[str] = None

@router.post("/race_brief")
async def agent_race_brief(req: RaceBriefRequest):
    verify_session(req.session_id)
    brief = build_race_brief(req.session_id, req.focus_driver)
    if brief is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "snapshot_not_ready",
                "session_id": req.session_id,
            },
        )
    return brief


# ── Context Pack ──────────────────────────────────────────────────────────

class ContextPackRequest(BaseModel):
    session_id: str
    query_type: str
    drivers: List[str] = []
    horizon_laps: int = 2

@router.post("/context_pack")
async def agent_context_pack(req: ContextPackRequest):
    verify_session(req.session_id)
    pack = build_context_pack(
        req.session_id, req.query_type, req.drivers, req.horizon_laps,
    )
    if pack is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "snapshot_not_ready",
                "session_id": req.session_id,
            },
        )
    return pack
