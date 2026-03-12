"""
Tool registry — exposes Pydantic-derived JSON schemas for every callable tool
so that Gemini (or any LLM) can discover and call them correctly.
"""

from typing import Any, Dict, List

from app.models.tool_models import (
    ResolveDriverRequest, ResolveDriverResponse,
    GetRaceContextRequest, GetRaceContextResponse,
    ProjectPitRejoinRequest, ProjectPitRejoinResponse,
    EstimateUndercutRequest, EstimateUndercutResponse,
    RecommendStrategyRequest, RecommendStrategyResponse,
)

REGISTRY_VERSION = "v1"

_TOOL_DEFS: List[Dict[str, Any]] = [
    {
        "name": "resolve_driver",
        "description": "Resolve a natural-language driver reference (e.g. 'Max', 'Leclerc') to an official 3-letter code.",
        "input_schema": ResolveDriverRequest.model_json_schema(),
        "output_schema": ResolveDriverResponse.model_json_schema(),
    },
    {
        "name": "get_race_context",
        "description": "Get the current race context: lap number, track status (SC/VSC/flag), and timestamp.",
        "input_schema": GetRaceContextRequest.model_json_schema(),
        "output_schema": GetRaceContextResponse.model_json_schema(),
    },
    {
        "name": "project_pit_rejoin",
        "description": "Project pit rejoin position and gaps using cached race snapshot and pit loss baseline.",
        "input_schema": ProjectPitRejoinRequest.model_json_schema(),
        "output_schema": ProjectPitRejoinResponse.model_json_schema(),
    },
    {
        "name": "estimate_undercut",
        "description": "Estimate the time gain/loss of an undercut: attacker pits now vs defender staying out for N laps.",
        "input_schema": EstimateUndercutRequest.model_json_schema(),
        "output_schema": EstimateUndercutResponse.model_json_schema(),
    },
    {
        "name": "recommend_strategy",
        "description": "Recommend the best strategy for a driver: pit_now, stay_out, cover_undercut, or extend_stint. Combines pit rejoin projection, undercut estimates vs adjacent competitors, tire age, track status (SC/VSC), and gap pressure. Returns reasons (bullet strings) and supporting evidence from computed projections.",
        "input_schema": RecommendStrategyRequest.model_json_schema(),
        "output_schema": RecommendStrategyResponse.model_json_schema(),
    },
]


def get_tool_registry() -> Dict[str, Any]:
    return {"version": REGISTRY_VERSION, "tools": _TOOL_DEFS}
