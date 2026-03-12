"""Unit tests for the deterministic undercut model."""

import pytest
from app.strategy.undercut_model import estimate_undercut


# ── Case 1: Attacker faster + new tire delta → positive gain ─────────────

def test_attacker_faster_positive_gain():
    """
    Attacker median ~80.0, defender median ~81.0.
    Fresh-tyre attacker = 80.0 - 0.6 = 79.4
    Over 2 laps:  defender = 2*81 = 162,  attacker = 2*79.4 + 21 = 179.8
    gain = 162 - 179.8 = -17.8 → negative (pit loss dominates short horizon)

    But over 10 laps: defender = 10*81 = 810, attacker = 10*79.4 + 21 = 815
    gain = 810 - 815 = -5 still negative.

    Actually for undercut to be positive the pace delta * horizon must exceed pit loss.
    Let's use a scenario where the defender is significantly slower.
    """
    att_hist = [79.0, 79.5, 79.2, 79.3]
    def_hist = [82.0, 82.5, 82.3, 82.1]  # 3+ seconds slower

    result = estimate_undercut(att_hist, def_hist, horizon_laps=10, pit_loss_s=21.0)

    assert result["expected_gain_s"] is not None
    assert result["expected_gain_s"] > 0  # Undercut is favourable
    assert result["confidence"] in ("low", "medium")
    assert result["assumptions"]["pit_loss_s"] == 21.0
    assert result["source"] == "replay"


# ── Case 2: Attacker slower → negative gain ──────────────────────────────

def test_attacker_slower_negative_gain():
    """
    Attacker is slower than defender. Undercut should NOT be recommended.
    """
    att_hist = [82.0, 82.5, 82.3]
    def_hist = [79.0, 79.5, 79.2]

    result = estimate_undercut(att_hist, def_hist, horizon_laps=2, pit_loss_s=21.0)

    assert result["expected_gain_s"] is not None
    assert result["expected_gain_s"] < 0  # Undercut unfavourable
    assert result["assumptions"] is not None


# ── Case 3: Insufficient pace data → null gain, low confidence ───────────

def test_insufficient_pace_data():
    att_hist = [80.0]  # Only 1 sample, need MIN_PACE_SAMPLES (3)
    def_hist = [81.0, 82.0, 83.0]

    result = estimate_undercut(att_hist, def_hist, horizon_laps=2)

    assert result["expected_gain_s"] is None
    assert result["confidence"] == "low"
    assert result["assumptions"] is None


def test_insufficient_defender_pace():
    att_hist = [80.0, 80.5, 80.2]
    def_hist = [81.0]  # Only 1 sample

    result = estimate_undercut(att_hist, def_hist, horizon_laps=2)

    assert result["expected_gain_s"] is None
    assert result["confidence"] == "low"


# ── Case 4: Horizon affects magnitude ────────────────────────────────────

def test_horizon_affects_magnitude():
    att_hist = [79.0, 79.5, 79.2]
    def_hist = [82.0, 82.5, 82.3]

    result_2 = estimate_undercut(att_hist, def_hist, horizon_laps=2, pit_loss_s=21.0)
    result_10 = estimate_undercut(att_hist, def_hist, horizon_laps=10, pit_loss_s=21.0)

    # Over a longer horizon, the tire advantage should accumulate more
    assert result_10["expected_gain_s"] > result_2["expected_gain_s"]


# ── Case 5: Exact-same pace → gain driven only by tire delta vs pit loss ─

def test_equal_pace():
    hist = [80.0, 80.0, 80.0]

    result = estimate_undercut(hist, hist, horizon_laps=2, pit_loss_s=21.0)

    # att_new = 80 - 0.6 = 79.4; defender_time = 160, attacker_time = 158.8 + 21 = 179.8
    # gain = 160 - 179.8 = -19.8  (pit loss far outweighs 2-lap advantage)
    assert result["expected_gain_s"] is not None
    assert result["expected_gain_s"] < 0
