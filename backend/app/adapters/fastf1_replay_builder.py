import fastf1
import pandas as pd
import math
from typing import List, Optional, Dict, Any

from app.models.snapshot_model import RaceSnapshot, DriverState, TireState, TrackStatus
from app.utils.time_utils import current_time_utc

def safe_float(val: Any) -> Optional[float]:
    if pd.isna(val):
        return None
    return float(val)

def safe_int(val: Any) -> Optional[int]:
    if pd.isna(val):
        return None
    return int(val)

def extract_snapshots(year: int, gp: str, session_identifier: str, session_id: str) -> List[RaceSnapshot]:
    """
    Downloads FastF1 data for a specific race and generates coarse (1 per lap) RaceSnapshots.
    """
    session = fastf1.get_session(year, gp, session_identifier)
    session.load(telemetry=False, weather=False, messages=True)

    laps = session.laps
    if laps.empty:
        raise ValueError("No lap data available for this session.")

    max_laps = int(laps['LapNumber'].max())
    snapshots: List[RaceSnapshot] = []

    # FastF1 doesn't cleanly give exact timestamps for the "start" of a lap for all drivers simultaneously,
    # so we will simulate progression by just iterating 1 to max_laps and creating a snapshot per lap boundary.
    for lap_num in range(1, max_laps + 1):
        lap_data = laps[laps['LapNumber'] == lap_num]
        if lap_data.empty:
            continue

        drivers_state: List[DriverState] = []
        
        # We need to sort by position to calculate gaps ahead/behind natively if FastF1 doesn't provide it
        # Sometimes FastF1 'Position' is NaN for DNF, so we handle it.
        lap_data_sorted = lap_data.dropna(subset=['Position']).sort_values('Position')

        leader_time = None
        prev_driver_time = None

        for idx, row in lap_data_sorted.iterrows():
            pos = safe_int(row.get('Position'))
            driver_code = str(row.get('Driver', "UNK"))
            
            # Times are Timedeltas in FastF1
            lap_time_dt = row.get('LapTime')
            last_lap_time_s = getattr(lap_time_dt, 'total_seconds', lambda: None)() if not pd.isna(lap_time_dt) else None

            # Calculate gaps manually using Time object (total race time elapsed for that driver)
            time_dt = row.get('Time')
            current_time_s = getattr(time_dt, 'total_seconds', lambda: None)() if not pd.isna(time_dt) else None

            gap_to_leader = None
            gap_ahead = None
            
            if current_time_s is not None:
                if pos == 1:
                    leader_time = current_time_s
                    gap_to_leader = 0.0
                    gap_ahead = None
                else:
                    if leader_time is not None:
                        gap_to_leader = max(0.0, current_time_s - leader_time)
                    if prev_driver_time is not None:
                        gap_ahead = max(0.0, current_time_s - prev_driver_time)
                
                prev_driver_time = current_time_s

            compound = str(row.get('Compound', ""))
            compound = compound if compound and compound != "nan" else None
            tire_age = safe_int(row.get('TyreLife'))

            tire_state = TireState(compound=compound, age=tire_age) if compound or tire_age is not None else None

            driver = DriverState(
                driver_code=driver_code,
                position=pos,
                gap_to_leader=gap_to_leader,
                gap_ahead=gap_ahead,
                gap_behind=None, # We calculate gap_behind in a second pass
                tire=tire_state,
                last_lap_time=last_lap_time_s
            )
            drivers_state.append(driver)

        # Second pass to populate gap_behind
        for i in range(len(drivers_state) - 1):
            if drivers_state[i+1].gap_ahead is not None:
                drivers_state[i].gap_behind = drivers_state[i+1].gap_ahead

        # Extract track status (coarse approximation for the lap)
        # FastF1 track_status is mostly integer codes, so we default to roughly GREEN/UNKNOWN for MVP
        flag = "GREEN"
        sc = False
        vsc = False
        track_status_obj = TrackStatus(sc=sc, vsc=vsc, flag=flag)

        # Create snapshot object
        # Note: We use the actual system UTC time here as a simulation timestamp placeholder. 
        # For replay, we just need ANY valid ISO string to fulfill the schema. The Replay worker will rewrite it 
        # to the *current* real-time when it injects it into Redis.
        snapshot = RaceSnapshot(
            session_id=session_id,
            timestamp_utc=current_time_utc(),  
            lap=lap_num,
            track_status=track_status_obj,
            drivers=drivers_state
        )
        snapshots.append(snapshot)

    return snapshots
