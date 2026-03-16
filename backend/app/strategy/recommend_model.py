"""Deterministic strategy recommendation model."""

from typing import Any, Dict, List, Optional, Tuple

from app.config.pit_loss_config import DEFAULT_PIT_LOSS_S
from app.config.strategy_thresholds import (
    DEFAULT_HORIZON_LAPS,
    MAX_POSITION_LOSS,
    OPPORTUNITY_GAP_S,
    PRESSURE_GAP_S,
    TIRE_AGE_WARN,
    UNDERCUT_MARGINAL_THRESHOLD_S,
    UNDERCUT_STRONG_THRESHOLD_S,
)
from app.models.snapshot_model import DriverState, RaceSnapshot
from app.strategy.pit_rejoin_model import project_pit_rejoin
from app.strategy.undercut_model import estimate_undercut


def _find_driver(snapshot: RaceSnapshot, code: str) -> Optional[DriverState]:
    for driver in snapshot.drivers:
        if driver.driver_code == code:
            return driver
    return None


def _find_adjacent(
    snapshot: RaceSnapshot, driver: DriverState
) -> Tuple[Optional[DriverState], Optional[DriverState]]:
    sorted_drivers = sorted(
        [item for item in snapshot.drivers if item.position is not None],
        key=lambda item: item.position,  # type: ignore[arg-type]
    )
    idx = None
    for i, item in enumerate(sorted_drivers):
        if item.driver_code == driver.driver_code:
            idx = i
            break
    if idx is None:
        return None, None

    ahead = sorted_drivers[idx - 1] if idx > 0 else None
    behind = sorted_drivers[idx + 1] if idx < len(sorted_drivers) - 1 else None
    return ahead, behind


def _driver_summary(driver: Optional[DriverState]) -> Optional[Dict[str, Any]]:
    if driver is None:
        return None
    return {
        "driver_code": driver.driver_code,
        "position": driver.position,
        "gap_to_leader_s": driver.gap_to_leader,
        "gap_ahead_s": driver.gap_ahead,
        "gap_behind_s": driver.gap_behind,
        "tire_compound": driver.tire.compound if driver.tire else None,
        "tire_age_laps": driver.tire.age if driver.tire else None,
        "last_lap_time_s": driver.last_lap_time,
    }


def _build_base_evidence(
    snapshot: RaceSnapshot,
    driver: DriverState,
    ahead: Optional[DriverState],
    behind: Optional[DriverState],
) -> Dict[str, Any]:
    return {
        "focus_driver": _driver_summary(driver),
        "cars_around": {
            "ahead": _driver_summary(ahead),
            "behind": _driver_summary(behind),
        },
        "track_status": {
            "flag": snapshot.track_status.flag,
            "sc": snapshot.track_status.sc,
            "vsc": snapshot.track_status.vsc,
        },
    }


def recommend_strategy(
    snapshot: RaceSnapshot,
    driver_code: str,
    pace_histories: Dict[str, List[float]],
    pit_loss_s: float = DEFAULT_PIT_LOSS_S,
) -> Dict[str, Any]:
    # Gate: strategy recommendations only apply during race sessions
    _RACE_SESSIONS = {"Race", "Sprint"}
    if snapshot.session_type and snapshot.session_type not in _RACE_SESSIONS:
        return {
            "action": "not_applicable",
            "not_applicable": True,
            "session_type": snapshot.session_type,
            "reason": (
                f"Strategy recommendations are only available during Race and Sprint sessions. "
                f"Current session type is '{snapshot.session_type}'."
            ),
            "timestamp_utc": snapshot.timestamp_utc,
            "lap": snapshot.lap,
        }

    driver = _find_driver(snapshot, driver_code)
    if driver is None:
        return _insufficient("Driver not found in snapshot", snapshot)

    ahead_driver, behind_driver = _find_adjacent(snapshot, driver)
    reasons: List[str] = []
    evidence = _build_base_evidence(snapshot, driver, ahead_driver, behind_driver)

    if snapshot.track_status.sc:
        reasons.append("Safety Car deployed; pit now for reduced time loss")
        return _result("pit_now", reasons, evidence, "medium", snapshot)
    if snapshot.track_status.vsc:
        reasons.append("Virtual Safety Car active; pit now for reduced pit loss")
        return _result("pit_now", reasons, evidence, "medium", snapshot)

    rejoin: Optional[Dict[str, Any]]
    try:
        rejoin = project_pit_rejoin(snapshot, driver_code, pit_loss_s)
        evidence["pit_rejoin"] = rejoin
    except ValueError:
        rejoin = None

    current_pos = driver.position
    position_loss = 0
    if rejoin and current_pos is not None:
        position_loss = rejoin["projected_position"] - current_pos

    undercut_ahead = None
    if (
        ahead_driver is not None
        and ahead_driver.driver_code in pace_histories
        and driver_code in pace_histories
    ):
        undercut_ahead = estimate_undercut(
            attacker_pace_hist=pace_histories[driver_code],
            defender_pace_hist=pace_histories[ahead_driver.driver_code],
            horizon_laps=DEFAULT_HORIZON_LAPS,
            pit_loss_s=pit_loss_s,
            timestamp_utc=snapshot.timestamp_utc,
        )
        evidence["undercut_vs_ahead"] = undercut_ahead

    undercut_behind = None
    if (
        behind_driver is not None
        and behind_driver.driver_code in pace_histories
        and driver_code in pace_histories
    ):
        undercut_behind = estimate_undercut(
            attacker_pace_hist=pace_histories[behind_driver.driver_code],
            defender_pace_hist=pace_histories[driver_code],
            horizon_laps=DEFAULT_HORIZON_LAPS,
            pit_loss_s=pit_loss_s,
            timestamp_utc=snapshot.timestamp_utc,
        )
        evidence["undercut_threat_from_behind"] = undercut_behind

    ahead_gain = None
    if undercut_ahead is not None:
        ahead_gain = undercut_ahead.get("expected_gain_s")

    behind_gain = None
    if undercut_behind is not None:
        behind_gain = undercut_behind.get("expected_gain_s")

    gap_ahead_val = driver.gap_ahead if driver.gap_ahead is not None else 99.0
    gap_behind_val = driver.gap_behind if driver.gap_behind is not None else 99.0
    tire_age = driver.tire.age if driver.tire else None

    if ahead_gain is not None and ahead_gain > UNDERCUT_STRONG_THRESHOLD_S:
        reasons.append(
            f"Strong undercut vs {ahead_driver.driver_code}: +{ahead_gain:.1f}s over {DEFAULT_HORIZON_LAPS} laps"
        )
        if rejoin and position_loss <= MAX_POSITION_LOSS:
            reasons.append(
                f"Projected rejoin is P{rejoin['projected_position']} with {position_loss} place(s) lost"
            )
            return _result("pit_now", reasons, evidence, "medium", snapshot)
        reasons.append(f"Projected rejoin loses {position_loss} positions, so the window is weak")

    if behind_gain is not None and behind_gain > UNDERCUT_STRONG_THRESHOLD_S:
        reasons.append(
            f"Undercut threat from {behind_driver.driver_code}: they gain +{behind_gain:.1f}s if they pit"
        )
        if gap_behind_val < PRESSURE_GAP_S:
            reasons.append(f"Gap behind is only {gap_behind_val:.1f}s, so cover the undercut")
            return _result("cover_undercut", reasons, evidence, "medium", snapshot)

    if tire_age is not None and tire_age > TIRE_AGE_WARN:
        reasons.append(f"Tire age is {tire_age} laps, so stint extension carries risk")
        if ahead_gain is not None and ahead_gain > UNDERCUT_MARGINAL_THRESHOLD_S:
            reasons.append(f"There is still a positive undercut opportunity of +{ahead_gain:.1f}s")
            return _result("pit_now", reasons, evidence, "medium", snapshot)
        if rejoin and position_loss <= MAX_POSITION_LOSS and gap_ahead_val <= OPPORTUNITY_GAP_S:
            reasons.append(
                f"Gap ahead is only {gap_ahead_val:.1f}s and projected rejoin is still acceptable"
            )
            return _result("pit_now", reasons, evidence, "medium", snapshot)

    if gap_behind_val > PRESSURE_GAP_S:
        reasons.append(f"Clear air behind with a {gap_behind_val:.1f}s gap supports extension")
        if tire_age is not None:
            reasons.append(f"Tire age is {tire_age} laps and still manageable")
        return _result("extend_stint", reasons, evidence, "medium", snapshot)

    if ahead_gain is not None and ahead_gain > UNDERCUT_MARGINAL_THRESHOLD_S:
        reasons.append(f"Marginal undercut opportunity of +{ahead_gain:.1f}s is available")
        if rejoin and position_loss <= 1 and gap_ahead_val <= OPPORTUNITY_GAP_S:
            reasons.append("Projected rejoin cost is limited and the target car is close ahead")
            return _result("pit_now", reasons, evidence, "low", snapshot)
        reasons.append("Pressure is moderate, so stay out and monitor the next lap")
        return _result("stay_out", reasons, evidence, "low", snapshot)

    if rejoin and position_loss > MAX_POSITION_LOSS:
        reasons.append(f"Projected rejoin at P{rejoin['projected_position']} loses too much track position")
    else:
        reasons.append("No strong pit signal is available right now")
    reasons.append("Stay out and wait for a stronger window or new threat")
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
        "source": snapshot.mode,
        "mode": snapshot.mode,
        "snapshot_ingest_ts_utc": snapshot.ingest_ts_utc,
        "source_ts_utc": snapshot.source_ts_utc,
        "lap": snapshot.lap,
    }


def _insufficient(msg: str, snapshot: RaceSnapshot) -> Dict[str, Any]:
    return {
        "recommended_action": "insufficient_data",
        "reasons": [msg],
        "supporting_evidence": {},
        "confidence": "low",
        "timestamp_utc": snapshot.timestamp_utc,
        "source": snapshot.mode,
        "mode": snapshot.mode,
        "snapshot_ingest_ts_utc": snapshot.ingest_ts_utc,
        "source_ts_utc": snapshot.source_ts_utc,
        "lap": snapshot.lap,
    }
