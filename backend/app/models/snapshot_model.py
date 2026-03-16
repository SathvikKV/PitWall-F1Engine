from pydantic import BaseModel, Field, field_validator
from typing import Optional, List

class TrackStatus(BaseModel):
    sc: Optional[bool] = None
    vsc: Optional[bool] = None
    flag: str

class TireState(BaseModel):
    compound: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=0)

class DriverState(BaseModel):
    driver_code: str
    position: Optional[int] = Field(default=None, ge=1)
    gap_to_leader: Optional[float] = Field(default=None, ge=0)
    gap_ahead: Optional[float] = Field(default=None, ge=0)
    gap_behind: Optional[float] = Field(default=None, ge=0)
    tire: Optional[TireState] = None
    last_lap_time: Optional[float] = Field(default=None, ge=0)

    @field_validator('driver_code')
    def validate_driver_code(cls, v):
        if len(v) != 3 or not v.isupper():
            if v != "UNK":
                raise ValueError("driver_code must be uppercase and 3 characters long, or 'UNK'")
        return v

class RaceSnapshot(BaseModel):
    session_id: str
    timestamp_utc: str
    lap: Optional[int] = Field(default=None, ge=0)
    track_status: TrackStatus
    drivers: List[DriverState]
    mode: str = "replay"                  # "replay" | "live"
    session_type: Optional[str] = None    # "Race" | "Sprint" | "Qualifying" | "Practice" | None
    ingest_ts_utc: Optional[str] = None
    source_ts_utc: Optional[str] = None

