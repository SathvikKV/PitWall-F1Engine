from datetime import datetime, timezone

def current_time_utc() -> str:
    """Returns the current UTC time as an ISO formatted string."""
    return datetime.now(timezone.utc).isoformat()
