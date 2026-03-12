# Tire model constants for MVP.
# These will be loaded per-circuit from Firestore in future tickets.

# Expected per-lap time advantage of fresh tires vs worn tires
NEW_TIRE_DELTA_S_PER_LAP: float = 0.6

# Maximum per-lap benefit (prevents unrealistic estimates)
MAX_TIRE_DELTA_S_PER_LAP: float = 1.2
