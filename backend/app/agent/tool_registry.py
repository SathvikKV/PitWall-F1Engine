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
    QueryWikipediaRequest, QueryWikipediaResponse,
)

REGISTRY_VERSION = "v1"

def clean_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Strip unsupported Pydantic keywords from JSON schema for Gemini."""
    cleaned = {}
    for k, v in schema.items():
        if k in ("title", "default"):
            continue
        if k == "anyOf":
            # Gemini doesn't support anyOf for optional fields well; just take the first type
            # (usually the actual type, and the second is 'null')
            if isinstance(v, list) and len(v) > 0:
                if "type" in v[0]:
                    cleaned["type"] = v[0]["type"]
            continue
            
        if isinstance(v, dict):
            cleaned[k] = clean_schema(v)
        elif isinstance(v, list):
            cleaned[k] = [clean_schema(i) if isinstance(i, dict) else i for i in v]
        else:
            cleaned[k] = v
            
    # Fix top-level object type if missing due to stripping
    if "type" not in cleaned and "properties" in cleaned:
        cleaned["type"] = "object"
        
    return cleaned

_TOOL_DEFS: List[Dict[str, Any]] = [
    {
        "name": "resolve_driver",
        "description": "Resolve a natural-language driver reference (e.g. 'Max', 'Leclerc') to an official 3-letter code.",
        "input_schema": clean_schema(ResolveDriverRequest.model_json_schema()),
        "output_schema": clean_schema(ResolveDriverResponse.model_json_schema()),
    },
    {
        "name": "get_race_context",
        "description": "Get the current race context: lap number, track status (SC/VSC/flag), and timestamp.",
        "input_schema": clean_schema(GetRaceContextRequest.model_json_schema()),
        "output_schema": clean_schema(GetRaceContextResponse.model_json_schema()),
    },
    {
        "name": "project_pit_rejoin",
        "description": "Project pit rejoin position and gaps using cached race snapshot and pit loss baseline.",
        "input_schema": clean_schema(ProjectPitRejoinRequest.model_json_schema()),
        "output_schema": clean_schema(ProjectPitRejoinResponse.model_json_schema()),
    },
    {
        "name": "estimate_undercut",
        "description": "Estimate the time gain/loss of an undercut: attacker pits now vs defender staying out for N laps.",
        "input_schema": clean_schema(EstimateUndercutRequest.model_json_schema()),
        "output_schema": clean_schema(EstimateUndercutResponse.model_json_schema()),
    },
    {
        "name": "recommend_strategy",
        "description": "Recommend the best strategy for a driver: pit_now, stay_out, cover_undercut, or extend_stint. Combines pit rejoin projection, undercut estimates vs adjacent competitors, tire age, track status (SC/VSC), and gap pressure. Returns reasons (bullet strings) and supporting evidence from computed projections.",
        "input_schema": clean_schema(RecommendStrategyRequest.model_json_schema()),
        "output_schema": clean_schema(RecommendStrategyResponse.model_json_schema()),
    },
    {
        "name": "query_wikipedia",
        "description": "Query Wikipedia for information about F1 rules, regulations, drivers, teams, circuits, or historical statistics.",
        "input_schema": clean_schema(QueryWikipediaRequest.model_json_schema()),
        "output_schema": clean_schema(QueryWikipediaResponse.model_json_schema()),
    },
]


def get_tool_registry() -> Dict[str, Any]:
    return {"version": REGISTRY_VERSION, "tools": _TOOL_DEFS}
