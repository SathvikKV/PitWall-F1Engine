"""
Deterministic strategy recommendation model.

Combines pit rejoin projection + undercut estimate + heuristics to
recommend one of:
  pit_now | stay_out | cover_undercut | extend_stint | insufficient_data

Pure computation — no I/O. All data must be passed in.
"""

from typing import Dict, Any, List, Optional

from app.models.snapshot_model import RaceSnapshot, DriverState
from app.strategy.pit_rejoin_model import project_pit_rejoin
from app.strategy.undercut_model import estimate_undercut
from app.config.pit_loss_config import DEFAULT_PIT_LOSS_S
from app.config.strategy_thresholds import (
    UNDERCUT_STRONG_THRESHOLD_S,
    UNDERCUT_MARGINAL_THRESHOLD_S,
    PRESSURE_GAP_S,
    OPPORTUNITY_GAP_S,
    MAX_POSITION_LOSS,
    TIRE_AGE_WARN,
    DEFAULT_HORIZON_LAPS,
)


def _find_driver(snapshot: RaceSnapshot, code: str) -> Optional[DriverState]:
    for d in snapshot.drivers:
        if d.driver_code == code:
            return d
    return None


def _find_adjacent(snapshot: RaceSnapshot, driver: DriverState):
    """Return (car_ahead_code, car_behind_code) based on position."""
    sorted_drivers = sorted(
        [d for d in snapshot.drivers if d.position is not None],
        key=lambda d: d.position,  # type: ignore[arg-type]
    )
    idx = None
    for i, d in enumerate(sorted_drivers):
        if d.driver_code == driver.driver_code:
            idx = i
            break
    if idx is None:
        return None, None
    ahead = sorted_drivers[idx - 1].driver_code if idx > 0 else None
    behind = sorted_drivers[idx + 1].driver_code if idx < len(sorted_drivers) - 1 else None
    return ahead, behind


def recommend_strategy(
    snapshot: RaceSnapshot,
    driver_code: str,
    pace_histories: Dict[str, List[float]],
    pit_loss_s: float = DEFAULT_PIT_LOSS_S,
) -> Dict[str, Any]:
    """
    Return a strategy recommendation dict.

    Parameters
    ----------
    snapshot : RaceSnapshot
    driver_code : 3-letter driver code
    pace_histories : {driver_code: [last N lap times]} for relevant drivers
    pit_loss_s : pit lane loss assumption
    """

    driver = _find_driver(snapshot, driver_code)
    if driver is None:
        return _insufficient("Driver not found in snapshot", snapshot)

    reasons: List[str] = []
    evidence: Dict[str, Any] = {}
    current_pos = driver.position

    # ── 1. Track status check ──────────────────────────────────────────
    ts = snapshot.track_status
    sc_active = ts.sc is True
    vsc_active = ts.vsc is True

    if sc_active:
        reasons.append("Safety Car deployed — pit now for minimal time loss")
        return _result(
            "pit_now", reasons, evidence, "medium", snapshot,
        )
    if vsc_active:
        reasons.append("Virtual Safety Car active — pit now for reduced pit loss")
        return _result(
            "pit_now", reasons, evidence, "medium", snapshot,
        )

    # ── 2. Pit rejoin projection ───────────────────────────────────────
    try:
        rejoin = project_pit_rejoin(snapshot, driver_code, pit_loss_s)
        evidence["pit_rejoin"] = rejoin
    except ValueError:
        rejoin = None

    position_loss = 0
    if rejoin and current_pos is not None:
        position_loss = rejoin["projected_position"] - current_pos

    # ── 3. Undercut vs car ahead ───────────────────────────────────────
    ahead_code, behind_code = _find_adjacent(snapshot, driver)

    undercut_ahead = None
    if ahead_code and ahead_code in pace_histories and driver_code in pace_histories:
        undercut_ahead = estimate_undercut(
            attacker_pace_hist=pace_histories[driver_code],
            defender_pace_hist=pace_histories[ahead_code],
            horizon_laps=DEFAULT_HORIZON_LAPS,
            pit_loss_s=pit_loss_s,
            timestamp_utc=snapshot.timestamp_utc,
        )
        evidence["undercut_vs_ahead"] = undercut_ahead

    # ── 4. Undercut threat from car behind ─────────────────────────────
    undercut_behind = None
    if behind_code and behind_code in pace_histories and driver_code in pace_histories:
        undercut_behind = estimate_undercut(
            attacker_pace_hist=pace_histories[behind_code],
            defender_pace_hist=pace_histories[driver_code],
            horizon_laps=DEFAULT_HORIZON_LAPS,
            pit_loss_s=pit_loss_s,
            timestamp_utc=snapshot.timestamp_utc,
        )
        evidence["undercut_threat_from_behind"] = undercut_behind

    # ── 5. Decision logic ──────────────────────────────────────────────

    # 5a. Strong undercut opportunity ahead
    ahead_gain = undercut_ahead["expected_gain_s"] if undercut_ahead and undercut_ahead["expected_gain_s"] is not None else None
    if ahead_gain is not None and ahead_gain > UNDERCUT_STRONG_THRESHOLD_S:
        reasons.append(f"Strong undercut vs {ahead_code}: +{ahead_gain:.1f}s over {DEFAULT_HORIZON_LAPS} laps")
        if position_loss <= MAX_POSITION_LOSS:
            reasons.append(f"Pit rejoin at P{rejoin['projected_position']}, losing {position_loss} place(s)")
            return _result("pit_now", reasons, evidence, "medium", snapshot)
        else:
            reasons.append(f"But pit rejoin costs {position_loss} positions — marginal call")

    # 5b. Undercut threat from behind — cover it
    behind_gain = undercut_behind["expected_gain_s"] if undercut_behind and undercut_behind["expected_gain_s"] is not None else None
    if behind_gain is not None and behind_gain > UNDERCUT_STRONG_THRESHOLD_S:
        reasons.append(f"Undercut threat from {behind_code}: they gain +{behind_gain:.1f}s if they pit")
        gap_behind_val = driver.gap_behind if driver.gap_behind is not None else 99.0
        if gap_behind_val < PRESSURE_GAP_S:
            reasons.append(f"Gap behind only {gap_behind_val:.1f}s — cover the undercut")
            return _result("cover_undercut", reasons, evidence, "medium", snapshot)

    # 5c. Tire age concern
    tire_age = driver.tire.age if driver.tire else None
    if tire_age is not None and tire_age > TIRE_AGE_WARN:
        reasons.append(f"Tire age {tire_age} laps — consider pitting")
        if ahead_gain is not None and ahead_gain > UNDERCUT_MARGINAL_THRESHOLD_S:
            reasons.append(f"Marginal undercut available (+{ahead_gain:.1f}s)")
            return _result("pit_now", reasons, evidence, "medium", snapshot)

    # 5d. Clear air / no pressure
    gap_behind_val = driver.gap_behind if driver.gap_behind is not None else 99.0
    if gap_behind_val > PRESSURE_GAP_S:
        reasons.append(f"Clear air behind ({gap_behind_val:.1f}s gap) — extend stint")
        if tire_age is not None:
            reasons.append(f"Tire age {tire_age} laps — still manageable")
        return _result("extend_stint", reasons, evidence, "medium", snapshot)

    # 5e. Marginal undercut, moderate pressure
    if ahead_gain is not None and ahead_gain > UNDERCUT_MARGINAL_THRESHOLD_S:
        reasons.append(f"Marginal undercut opportunity (+{ahead_gain:.1f}s)")
        reasons.append("Under moderate pressure — stay out and monitor")
        return _result("stay_out", reasons, evidence, "low", snapshot)

    # Default: stay out
    reasons.append("No strong signal — stay out and wait for better window")
    return _result("stay_out", reasons, evidence, "low", snapshot)


def _result(
    action: str,
    reasons: List[str],
    evidence: Dict[str, Any],
    confidence: str,
    snapshot: RaceSnapshot,
) -> Dict[str, Any]:
    return {
        "recommended_action": action,
        "reasons": reasons,
        "supporting_evidence": evidence,
        "confidence": confidence,
        "timestamp_utc": snapshot.timestamp_utc,
        "source": "replay",
        "lap": snapshot.lap,
    }


def _insufficient(msg: str, snapshot: RaceSnapshot) -> Dict[str, Any]:
    return {
        "recommended_action": "insufficient_data",
        "reasons": [msg],
        "supporting_evidence": {},
        "confidence": "low",
        "timestamp_utc": snapshot.timestamp_utc,
        "source": "replay",
        "lap": snapshot.lap,
    }
