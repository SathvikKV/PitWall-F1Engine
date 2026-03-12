from fastapi import HTTPException, status
from app.services.session_service import session_exists
from app.utils.time_utils import current_time_utc

def verify_session(session_id: str):
    """Function to check if a session exists before allowing tool execution."""
    if not session_exists(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail={
                "error": "session_not_found", 
                "session_id": session_id, 
                "timestamp_utc": current_time_utc()
            }
        )
