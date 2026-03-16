"""
OpenF1 Data Explorer — 2026 Australian GP
==========================================
Queries every available endpoint for the 2026 Australian GP race session
and prints field schemas + sample rows so you can see what's available.

Usage:
    python scripts/explore_aus_2026.py

Credentials are read from backend/.env (OPENF1_USERNAME / OPENF1_PASSWORD).
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

# ── Load .env ─────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

USERNAME = os.getenv("OPENF1_USERNAME", "")
PASSWORD = os.getenv("OPENF1_PASSWORD", "")
BASE_URL = "https://api.openf1.org/v1"

# ── Auth ──────────────────────────────────────────────────────────────────────

async def get_token(client: httpx.AsyncClient) -> Optional[str]:
    if not USERNAME or not PASSWORD:
        print("⚠  No credentials found — using unauthenticated (free tier, historical only)")
        return None
    # OAuth2 password flow — OpenF1 sponsor auth
    try:
        resp = await client.post(
            "https://api.openf1.org/token",
            data={"username": USERNAME, "password": PASSWORD, "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token") or data.get("token")
            if token:
                print(f"✅ Authenticated as {USERNAME}\n")
                return token
        print(f"⚠  Token endpoint returned {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"⚠  Auth failed: {e}")
    return None


def auth_headers(token: Optional[str]) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


# ── HTTP helper ───────────────────────────────────────────────────────────────

async def get(
    endpoint: str,
    params: Dict[str, Any],
    client: httpx.AsyncClient,
    token: Optional[str],
) -> List[Dict[str, Any]]:
    url = f"{BASE_URL}/{endpoint}"
    try:
        resp = await client.get(url, params=params, headers=auth_headers(token), timeout=15)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        return [{"_error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}]
    except Exception as e:
        return [{"_error": str(e)}]


# ── Pretty printer ────────────────────────────────────────────────────────────

DIVIDER = "─" * 70

def print_endpoint(name: str, data: List[Dict[str, Any]], max_rows: int = 3):
    print(f"\n{'═' * 70}")
    print(f"  📡 {name.upper()}")
    print(f"{'═' * 70}")

    if not data:
        print("  (no data returned)")
        return

    if "_error" in (data[0] if data else {}):
        print(f"  ❌ Error: {data[0]['_error']}")
        return

    # Field schema
    all_keys = set()
    for row in data:
        all_keys.update(row.keys())
    print(f"  Fields ({len(all_keys)}): {', '.join(sorted(all_keys))}")
    print(f"  Rows returned: {len(data)}")
    print(f"\n  Sample rows (up to {max_rows}):")
    print(DIVIDER)

    for row in data[:max_rows]:
        print(json.dumps(row, indent=4, default=str))
        print(DIVIDER)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 70)
    print("  OpenF1 Explorer — 2026 Australian GP")
    print("=" * 70)

    async with httpx.AsyncClient() as client:
        token = await get_token(client)

        # Step 1: Find the Australian GP meeting
        print("\n🔍 Finding 2026 Australian GP meeting...")
        meetings = await get("meetings", {"year": 2026, "country_name": "Australia"}, client, token)
        if not meetings or "_error" in meetings[0]:
            print(f"  ❌ Could not find meeting: {meetings}")
            sys.exit(1)

        meeting = meetings[0]
        meeting_key = meeting["meeting_key"]
        print(f"  ✅ Meeting: {meeting.get('meeting_official_name')}")
        print(f"     Key: {meeting_key} | Location: {meeting.get('location')}")
        print(f"     Start: {meeting.get('date_start')} | End: {meeting.get('date_end')}")

        # Step 2: Find sessions for this meeting
        print(f"\n🔍 Sessions for meeting {meeting_key}...")
        sessions = await get("sessions", {"meeting_key": meeting_key}, client, token)
        print_endpoint("sessions", sessions, max_rows=10)

        # Find the race session
        race_session = next(
            (s for s in sessions if "Race" in (s.get("session_name") or "") and "Sprint" not in (s.get("session_name") or "")),
            sessions[-1] if sessions else None,
        )
        if not race_session or "_error" in race_session:
            print("  ❌ Could not find race session")
            sys.exit(1)

        session_key = race_session["session_key"]
        print(f"\n🏁 Race session key: {session_key} ({race_session.get('session_name')})")
        print(f"   Start: {race_session.get('date_start')} | End: {race_session.get('date_end')}\n")

        # Step 3: Hit all endpoints for this session
        params = {"session_key": session_key}

        # Drivers
        data = await get("drivers", params, client, token)
        print_endpoint("drivers", data, max_rows=5)
        # Capture driver numbers for later telemetry sampling
        driver_numbers = [d["driver_number"] for d in data if not isinstance(d, dict) or "_error" not in d]
        sample_driver = driver_numbers[0] if driver_numbers else 1

        # Intervals (real-time gaps)
        data = await get("intervals", params, client, token)
        print_endpoint("intervals", data, max_rows=3)

        # Laps
        data = await get("laps", params, client, token)
        print_endpoint("laps", data[:5] if data else data, max_rows=3)

        # Stints (tire data)
        data = await get("stints", params, client, token)
        print_endpoint("stints", data, max_rows=5)

        # Pit stops
        data = await get("pit", params, client, token)
        print_endpoint("pit", data, max_rows=5)

        # Position changes
        data = await get("position", params, client, token)
        print_endpoint("position", data, max_rows=3)

        # Race control (flags, SC, VSC, messages)
        data = await get("race_control", params, client, token)
        print_endpoint("race_control", data, max_rows=5)

        # Car telemetry (3.7 Hz — sample one driver, a few rows)
        car_data = await get("car_data", {**params, "driver_number": sample_driver}, client, token)
        print_endpoint(f"car_data (driver {sample_driver})", car_data[:5] if car_data and "_error" not in car_data[0] else car_data, max_rows=3)

        # Location (3.7 Hz — sample one driver)
        loc_data = await get("location", {**params, "driver_number": sample_driver}, client, token)
        print_endpoint(f"location (driver {sample_driver}, sample)", loc_data[:5] if loc_data and "_error" not in loc_data[0] else loc_data, max_rows=3)

        # Weather
        data = await get("weather", {"meeting_key": meeting_key}, client, token)
        print_endpoint("weather", data, max_rows=3)

        # Overtakes
        data = await get("overtakes", params, client, token)
        print_endpoint("overtakes", data, max_rows=5)

        # Session result
        data = await get("session_result", params, client, token)
        print_endpoint("session_result (final standings)", data, max_rows=5)

        # Starting grid (uses the qualifying session)
        qual_session = next(
            (s for s in sessions if "Qualifying" in (s.get("session_name") or "") and "Sprint" not in (s.get("session_name") or "")),
            None,
        )
        if qual_session:
            grid_data = await get("starting_grid", {"session_key": qual_session["session_key"]}, client, token)
            print_endpoint("starting_grid", grid_data, max_rows=5)
        else:
            print("\n  ℹ  No qualifying session found for starting grid")

        # Championship standings
        data = await get("championship_drivers", {"session_key": session_key}, client, token)
        print_endpoint("championship_drivers", data, max_rows=5)

        data = await get("championship_teams", {"session_key": session_key}, client, token)
        print_endpoint("championship_teams", data, max_rows=5)

        # Team radio clips
        data = await get("team_radio", params, client, token)
        print_endpoint("team_radio", data, max_rows=3)

        print(f"\n{'=' * 70}")
        print("  ✅ Exploration complete!")
        print(f"  Meeting key: {meeting_key} | Race session key: {session_key}")
        print(f"{'=' * 70}\n")


if __name__ == "__main__":
    asyncio.run(main())
