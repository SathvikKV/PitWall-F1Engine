from app.services.redis_client import get_json, set_json
from app.utils.time_utils import current_time_utc

def get_session_key(session_id: str) -> str:
    return f"session:{session_id}"

def session_exists(session_id: str) -> bool:
    """Check if session exists in Redis."""
    key = get_session_key(session_id)
    return get_json(key) is not None

def create_session(session_id: str) -> None:
    """Create a new session spanning indefinitely."""
    key = get_session_key(session_id)
    set_json(key, {"created_at": current_time_utc(), "session_id": session_id})
