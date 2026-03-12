# PitWall Web — F1 Strategy Dashboard

## Prerequisites

- Node.js 18+
- PitWall backend running on `http://localhost:8080`
- Redis running on `localhost:6379`

## Quick Start

```bash
cd web
npm install
cp .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Demo Flow

1. Click **Create** to register the session.
2. Click **▶ Start Replay** — the Race Brief panel will begin updating every 1.5 s.
3. Watch lap numbers advance in the left panel.
4. Enter a driver code (e.g. `NOR`) and click **Run Pit Rejoin** — an evidence card appears in the center.
5. Set attacker / defender (e.g. `NOR` vs `PIA`) and click **Run Undercut** — another card appears.
6. Click any card header to expand assumptions.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:8080` | Backend API base URL |
