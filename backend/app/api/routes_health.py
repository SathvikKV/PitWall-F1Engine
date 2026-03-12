from fastapi import APIRouter
from app.utils.time_utils import current_time_utc

router = APIRouter()

@router.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp_utc": current_time_utc()
    }
