from fastapi import APIRouter, Depends
from app.models.tool_models import (
    ResolveDriverRequest, ResolveDriverResponse,
    GetRaceContextRequest, GetRaceContextResponse,
    ProjectPitRejoinRequest, ProjectPitRejoinResponse, PitRejoinAssumptions,
    EstimateUndercutRequest, EstimateUndercutResponse, UndercutAssumptions,
    RecommendStrategyRequest, RecommendStrategyResponse
)
from app.models.snapshot_model import TrackStatus
from app.deps import verify_session
from app.services.snapshot_service import get_latest_snapshot
from app.utils.time_utils import current_time_utc
from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/tools", tags=["tools"])

def require_snapshot(session_id: str) -> dict:
    verify_session(session_id)
    snapshot = get_latest_snapshot(session_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "snapshot_not_ready",
                "session_id": session_id,
                "message": "Session exists but no telemetry snapshot received yet."
            }
        )
    return snapshot

@router.post("/resolve_driver", response_model=ResolveDriverResponse)
async def resolve_driver(req: ResolveDriverRequest):
    snap = require_snapshot(req.session_id)
    return ResolveDriverResponse(
        driver_code="UNK", # Stub logic still
        timestamp_utc=snap["timestamp_utc"],
        source="replay|live",
        lap=snap.get("lap"),
        mode=snap.get("mode"),
        snapshot_ingest_ts_utc=snap.get("ingest_ts_utc"),
    )

@router.post("/get_race_context", response_model=GetRaceContextResponse)
async def get_race_context(req: GetRaceContextRequest):
    snap = require_snapshot(req.session_id)
    # Map the dict back to TrackStatus model
    ts_dict = snap.get("track_status", {"flag": "UNKNOWN"})
    
    return GetRaceContextResponse(
        lap=snap.get("lap"),
        track_status=TrackStatus(**ts_dict),
        timestamp_utc=snap["timestamp_utc"],
        source="replay|live",
        mode=snap.get("mode"),
        snapshot_ingest_ts_utc=snap.get("ingest_ts_utc"),
    )

@router.post("/project_pit_rejoin", response_model=ProjectPitRejoinResponse)
async def project_pit_rejoin(req: ProjectPitRejoinRequest):
    snap = require_snapshot(req.session_id)

    # Hydrate the dict into a typed RaceSnapshot for the model
    from app.models.snapshot_model import RaceSnapshot as SnapModel
    from app.strategy.pit_rejoin_model import project_pit_rejoin as compute_rejoin
    from app.config.pit_loss_config import DEFAULT_PIT_LOSS_S

    snapshot_obj = SnapModel(**snap)

    try:
        result = compute_rejoin(snapshot_obj, req.driver_code, DEFAULT_PIT_LOSS_S)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "driver_not_found",
                "driver_code": req.driver_code,
                "message": str(exc),
            },
        )

    return ProjectPitRejoinResponse(
        projected_position=result["projected_position"],
        gap_ahead_s=result["gap_ahead_s"],
        gap_behind_s=result["gap_behind_s"],
        assumptions=PitRejoinAssumptions(**result["assumptions"]),
        confidence=result["confidence"],
        timestamp_utc=result["timestamp_utc"],
        source=result["source"],
        lap=snap.get("lap"),
        mode=snap.get("mode"),
        snapshot_ingest_ts_utc=snap.get("ingest_ts_utc"),
    )

@router.post("/estimate_undercut", response_model=EstimateUndercutResponse)
async def estimate_undercut(req: EstimateUndercutRequest):
    snap = require_snapshot(req.session_id)

    from app.services.snapshot_service import get_pace_history
    from app.strategy.undercut_model import estimate_undercut as compute_undercut
    from app.config.pit_loss_config import DEFAULT_PIT_LOSS_S

    att_hist = get_pace_history(req.session_id, req.attacker)
    def_hist = get_pace_history(req.session_id, req.defender)

    result = compute_undercut(
        attacker_pace_hist=att_hist,
        defender_pace_hist=def_hist,
        horizon_laps=req.horizon_laps,
        pit_loss_s=DEFAULT_PIT_LOSS_S,
        timestamp_utc=snap["timestamp_utc"],
    )

    assumptions = None
    if result["assumptions"]:
        assumptions = UndercutAssumptions(**result["assumptions"])

    return EstimateUndercutResponse(
        expected_gain_s=result["expected_gain_s"],
        horizon_laps=result["horizon_laps"],
        assumptions=assumptions,
        confidence=result["confidence"],
        timestamp_utc=result["timestamp_utc"],
        source=result["source"],
        lap=snap.get("lap"),
        mode=snap.get("mode"),
        snapshot_ingest_ts_utc=snap.get("ingest_ts_utc"),
    )

@router.post("/recommend_strategy", response_model=RecommendStrategyResponse)
async def recommend_strategy(req: RecommendStrategyRequest):
    snap = require_snapshot(req.session_id)

    from app.models.snapshot_model import RaceSnapshot as SnapModel
    from app.strategy.recommend_model import recommend_strategy as compute_recommend
    from app.services.snapshot_service import get_pace_history

    snapshot_obj = SnapModel(**snap)

    # Gather pace histories for all drivers in snapshot
    pace_histories = {}
    for d in snapshot_obj.drivers:
        hist = get_pace_history(req.session_id, d.driver_code)
        if hist:
            pace_histories[d.driver_code] = hist

    try:
        result = compute_recommend(snapshot_obj, req.driver_code, pace_histories)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "driver_not_found",
                "driver_code": req.driver_code,
                "message": str(exc),
            },
        )

    return RecommendStrategyResponse(
        recommended_action=result["recommended_action"],
        reasons=result.get("reasons", []),
        supporting_evidence=result.get("supporting_evidence", {}),
        confidence=result["confidence"],
        lap=result.get("lap"),
        timestamp_utc=result["timestamp_utc"],
        source=result["source"],
    )

