# Strategy recommendation thresholds.
# Used by recommend_model to decide between actions.

# Undercut is "strong" if expected gain exceeds this (seconds over horizon)
UNDERCUT_STRONG_THRESHOLD_S: float = 0.8

# Undercut is "marginal" if gain is positive but below the strong threshold
UNDERCUT_MARGINAL_THRESHOLD_S: float = 0.2

# If gap_behind is smaller than this, driver is under pressure
PRESSURE_GAP_S: float = 1.5

# If gap_ahead is smaller than this, there's an undercut opportunity
OPPORTUNITY_GAP_S: float = 2.0

# If pit rejoin position is worse by more than this many places, prefer stay_out
MAX_POSITION_LOSS: int = 4

# Tire age (laps) above which stint extension becomes risky
TIRE_AGE_WARN: int = 20

# Minimum undercut horizon laps for the internal calculation
DEFAULT_HORIZON_LAPS: int = 2
