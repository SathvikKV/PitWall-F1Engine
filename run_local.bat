@echo off
echo Starting PitWall-F1Engine Local Environment...

echo.
echo =======================================================
echo [1/3] Starting Redis via Docker...
echo =======================================================
docker run -p 6379:6379 -d redis:7

echo.
echo =======================================================
echo [2/3] Starting Backend (FastAPI on port 8080)...
echo =======================================================
start "PitWall Backend" cmd /k "cd backend && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --host 0.0.0.0 --port 8080"

echo.
echo =======================================================
echo [3/3] Starting Frontend (Next.js on port 3000)...
echo =======================================================
start "PitWall Frontend" cmd /k "cd web && npm run dev"

echo.
echo =======================================================
echo Launch sequence initiated!
echo =======================================================
echo - Backend should be running at: http://localhost:8080
echo - Frontend should be running at: http://localhost:3000
echo - Redis should be running at: localhost:6379
echo.
echo Note: This script assumes you have already created the .env files
echo and installed dependencies as described in LOCAL_SETUP.md.
echo.
echo (You can close this window at any time. The services are running in their own windows.)
pause
