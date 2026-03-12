"""
Deterministic undercut / overcut estimation model.

Compares the projected time over `horizon_laps` for:
  - Attacker: pits now (incurs pit_loss_s), runs on fresh tyres
  - Defender: stays out on old tyres, pits later

A positive `expected_gain_s` means the undercut is favourable for the attacker.
"""

from statistics import median
from typing import Dict, Any, List, Optional

from app.config.pit_loss_config import DEFAULT_PIT_LOSS_S
from app.config.tire_config import NEW_TIRE_DELTA_S_PER_LAP, MAX_TIRE_DELTA_S_PER_LAP

# Minimum number of recent laps needed for a credible pace estimate
MIN_PACE_SAMPLES = 3


def estimate_undercut(
    attacker_pace_hist: List[float],
    defender_pace_hist: List[float],
    horizon_laps: int,
    pit_loss_s: float = DEFAULT_PIT_LOSS_S,
    new_tire_delta: float = NEW_TIRE_DELTA_S_PER_LAP,
    timestamp_utc: str = "",
) -> Dict[str, Any]:
    """
    Return a dict matching ``EstimateUndercutResponse``.

    Algorithm (deterministic, no randomness):
      1. Compute recent pace medians from the last 3 entries of each history.
      2. Estimate attacker pace on fresh tyres:
             att_new = att_median - new_tire_delta
         (capped so maximum benefit = MAX_TIRE_DELTA_S_PER_LAP).
      3. Defender time over horizon = horizon * def_median
         Attacker time over horizon = horizon * att_new + pit_loss_s
      4. gain = defender_time - attacker_time
    """

    insufficient = (
        len(attacker_pace_hist) < MIN_PACE_SAMPLES
        or len(defender_pace_hist) < MIN_PACE_SAMPLES
    )
    if insufficient:
        return {
            "expected_gain_s": None,
            "horizon_laps": horizon_laps,
            "assumptions": None,
            "confidence": "low",
            "timestamp_utc": timestamp_utc,
            "source": "replay",
        }

    # --- Pace medians (last 3 laps) ---------------------------------------
    att_median = median(attacker_pace_hist[-3:])
    def_median = median(defender_pace_hist[-3:])

    # --- Attacker fresh-tyre pace -----------------------------------------
    delta = min(new_tire_delta, MAX_TIRE_DELTA_S_PER_LAP)
    att_new = att_median - delta

    # --- Time comparison over horizon -------------------------------------
    defender_time = horizon_laps * def_median
    attacker_time = horizon_laps * att_new + pit_loss_s

    gain = round(defender_time - attacker_time, 2)

    confidence = "medium" if abs(gain) > 0.5 else "low"

    return {
        "expected_gain_s": gain,
        "horizon_laps": horizon_laps,
        "assumptions": {
            "pit_loss_s": pit_loss_s,
            "new_tire_delta_s_per_lap": delta,
            "attacker_pace_median_s": round(att_median, 3),
            "defender_pace_median_s": round(def_median, 3),
        },
        "confidence": confidence,
        "timestamp_utc": timestamp_utc,
        "source": "replay",
    }
