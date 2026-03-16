from pydantic import BaseModel, Field
from typing import Optional, List
from app.models.snapshot_model import TrackStatus

# Resolve Driver
class ResolveDriverRequest(BaseModel):
    session_id: str
    driver_reference: str

class ResolveDriverResponse(BaseModel):
    driver_code: str
    timestamp_utc: str
    source: str = "stub"
    lap: Optional[int] = None
    mode: Optional[str] = None
    snapshot_ingest_ts_utc: Optional[str] = None

# Get Race Context
class GetRaceContextRequest(BaseModel):
    session_id: str

class GetRaceContextResponse(BaseModel):
    lap: Optional[int] = None
    track_status: TrackStatus
    timestamp_utc: str
    source: str = "stub"
    mode: Optional[str] = None
    session_type: Optional[str] = None   # "Race" | "Sprint" | "Qualifying" | "Practice" | None
    snapshot_ingest_ts_utc: Optional[str] = None

# Project Pit Rejoin
class ProjectPitRejoinRequest(BaseModel):
    session_id: str
    driver_code: str

class PitRejoinAssumptions(BaseModel):
    pit_lane_loss_s: Optional[float] = None
    traffic_loss_s: Optional[float] = None

class ProjectPitRejoinResponse(BaseModel):
    projected_position: Optional[int] = None
    gap_ahead_s: Optional[float] = None
    gap_behind_s: Optional[float] = None
    assumptions: PitRejoinAssumptions
    confidence: str = "low"
    timestamp_utc: str
    source: str = "stub"
    lap: Optional[int] = None
    mode: Optional[str] = None
    snapshot_ingest_ts_utc: Optional[str] = None

# Estimate Undercut
class EstimateUndercutRequest(BaseModel):
    session_id: str
    attacker: str
    defender: str
    horizon_laps: int = 2

class UndercutAssumptions(BaseModel):
    pit_loss_s: Optional[float] = None
    new_tire_delta_s_per_lap: Optional[float] = None
    attacker_pace_median_s: Optional[float] = None
    defender_pace_median_s: Optional[float] = None

class EstimateUndercutResponse(BaseModel):
    expected_gain_s: Optional[float] = None
    horizon_laps: Optional[int] = None
    assumptions: Optional[UndercutAssumptions] = None
    confidence: str = "low"
    timestamp_utc: str
    source: str = "stub"
    lap: Optional[int] = None
    mode: Optional[str] = None
    snapshot_ingest_ts_utc: Optional[str] = None

# Recommend Strategy
class RecommendStrategyRequest(BaseModel):
    session_id: str
    driver_code: str
    objective: str = "race_time"

class RecommendStrategyResponse(BaseModel):
    recommended_action: str = "insufficient_data"
    reasons: List[str] = Field(default_factory=list)
    supporting_evidence: dict = Field(default_factory=dict)
    confidence: str = "low"
    lap: Optional[int] = None
    timestamp_utc: str
    source: str = "stub"
    mode: Optional[str] = None
    snapshot_ingest_ts_utc: Optional[str] = None
    source_ts_utc: Optional[str] = None

# Query Wikipedia
class QueryWikipediaRequest(BaseModel):
    query: str

class QueryWikipediaResponse(BaseModel):
    summary: str
    url: Optional[str] = None
    error: Optional[str] = None
