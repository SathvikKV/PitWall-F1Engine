# Local Setup Guide

This guide provides step-by-step instructions on how to launch the PitWall-F1Engine application locally.

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Docker** (for running Redis locally)

## Step 1: Start Redis

The backend requires Redis for caching and session management. You can spin up a local instance using Docker:

```bash
docker run -p 6379:6379 -d redis:7
```

*Redis will now be accessible at `localhost:6379`.*

## Step 2: Configure and Run the Backend

The backend is built with FastAPI and runs on port 8080.

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create your environment variables file:
   ```bash
   cp .env.example .env
   ```
   *Note: Ensure you populate your `.env` file with the necessary API keys (e.g., Gemini / Google GenAI keys) before running.*

3. Set up a Python virtual environment and activate it:
   ```bash
   python -m venv .venv
   
   # On Windows:
   .venv\Scripts\activate
   
   # On macOS/Linux:
   source .venv/bin/activate
   ```

4. Install the dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

5. Start the backend server:
   ```bash
   uvicorn app.main:app --reload --port 8080
   ```

## Step 3: Configure and Run the Frontend (Web)

The web frontend is built with Next.js and React, and it connects to the backend locally.

1. Open a new terminal and navigate to the web directory:
   ```bash
   cd web
   ```

2. Create your environment variables file:
   ```bash
   cp .env.example .env.local
   ```
   *(By default, this sets `NEXT_PUBLIC_BACKEND_URL` to `http://localhost:8080`.)*

3. Install the dependencies:
   ```bash
   npm install
   ```

4. Start the frontend development server:
   ```bash
   npm run dev
   ```

## Step 4: Access the Application

1. Open your browser and navigate to **[http://localhost:3000](http://localhost:3000)**.
2. Click **Create** to register a new session.
3. Click **▶ Start Replay** to begin the live data ingestion replay.
4. Use the interface to query driver data, run pit rejoin scenarios, or undercut analyses!
