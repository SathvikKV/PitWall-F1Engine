"""
OpenF1 async HTTP client.

Handles authentication (sponsor bearer token) and REST requests.
Falls back to unauthenticated requests for historical endpoints
when no credentials are configured.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)

BASE_URL = settings.OPENF1_BASE_URL.rstrip("/")

# ── Token cache (module-level, per-process) ──────────────────────────────────

_token: Optional[str] = None
_token_expiry: float = 0.0
_token_lock = asyncio.Lock()


async def _fetch_token(client: httpx.AsyncClient) -> Optional[str]:
    """Authenticate with OpenF1 and return a bearer token."""
    username = settings.OPENF1_USERNAME
    password = settings.OPENF1_PASSWORD
    if not username or not password:
        logger.debug("No OpenF1 credentials configured — using unauthenticated (free tier).")
        return None

    try:
        # OpenF1 uses OAuth2 password grant with form-encoded body
        resp = await client.post(
            "https://api.openf1.org/token",
            data={"username": username, "password": password, "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token") or data.get("token")
            if token:
                logger.info("OpenF1 token minted successfully.")
                return token
        logger.warning("OpenF1 auth response %s: %s", resp.status_code, resp.text[:200])
        return None
    except Exception as exc:
        logger.error("OpenF1 auth failed: %s", exc)
        return None


async def get_token(client: httpx.AsyncClient) -> Optional[str]:
    """Return a valid bearer token, refreshing if needed."""
    global _token, _token_expiry
    async with _token_lock:
        if _token and time.monotonic() < _token_expiry:
            return _token
        _token = await _fetch_token(client)
        # Tokens are valid for 1 hour; refresh 5 min early
        _token_expiry = time.monotonic() + 3300.0
        return _token


def _auth_headers(token: Optional[str]) -> Dict[str, str]:
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


async def openf1_get(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    """
    GET from `BASE_URL/endpoint` with optional query params.
    Automatically injects auth header if credentials are configured.
    Returns [] on any error.
    """
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    _own_client = client is None
    if _own_client:
        client = httpx.AsyncClient(timeout=10.0)

    try:
        token = await get_token(client)
        resp = await client.get(url, params=params or {}, headers=_auth_headers(token))
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("OpenF1 GET %s returned %s: %s", url, exc.response.status_code, exc.response.text[:200])
        return []
    except Exception as exc:
        logger.error("OpenF1 GET %s failed: %s", url, exc)
        return []
    finally:
        if _own_client:
            await client.aclose()


# ── Typed endpoint helpers ────────────────────────────────────────────────────

async def fetch_intervals(session_key: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Latest interval/gap data (~4 s cadence). Returns one row per driver."""
    return await openf1_get("intervals", {"session_key": session_key}, client)


async def fetch_stints(session_key: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Stint compound + age data for the session."""
    return await openf1_get("stints", {"session_key": session_key}, client)


async def fetch_laps(session_key: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """All lap records for the session."""
    return await openf1_get("laps", {"session_key": session_key}, client)


async def fetch_race_control(session_key: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Race control messages (flags, SC, VSC)."""
    return await openf1_get("race_control", {"session_key": session_key}, client)


async def fetch_drivers(session_key: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Driver metadata: number → name_acronym mapping."""
    return await openf1_get("drivers", {"session_key": session_key}, client)


async def fetch_sessions(session_key: str = "latest") -> List[Dict[str, Any]]:
    """Session metadata — useful for listing available sessions."""
    return await openf1_get("sessions", {"session_key": session_key})

async def fetch_location(session_key: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Driver location (x, y, z) telemetry for the session."""
    return await openf1_get("location", {"session_key": session_key}, client)


async def fetch_session_info(
    session_key: str, client: httpx.AsyncClient
) -> Dict[str, Any]:
    """
    Return session metadata for a given session_key.
    Includes session_name ("Race", "Qualifying", "Practice 1", etc.) and
    session_type ("Race", "Qualifying", "Practice", "Sprint Qualifying", ...).
    Returns {} if not found.
    """
    rows = await openf1_get("sessions", {"session_key": session_key}, client)
    if rows and isinstance(rows, list) and "_error" not in rows[0]:
        return rows[0]
    return {}
