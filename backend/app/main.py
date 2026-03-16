from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.api import routes_health, routes_tools, routes_admin, routes_agent, routes_live
from app.services.session_service import create_session
from app.utils.time_utils import current_time_utc

app = FastAPI(title="PitWall Tools API")

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "PitWall Backend API",
        "docs": "/docs"
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_health.router)
app.include_router(routes_tools.router)
app.include_router(routes_admin.router)
app.include_router(routes_agent.router)
app.include_router(routes_live.router)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.errors()}
    )

class CreateSessionRequest(BaseModel):
    session_id: str

@app.post("/admin/session/create")
async def create_session_endpoint(req: CreateSessionRequest):
    create_session(req.session_id)
    return {
        "status": "created",
        "session_id": req.session_id,
        "timestamp_utc": current_time_utc()
    }
