# PitWall Live Backend

Real-Time AI Race Engineer (Gemini Live + GCP).

## Local Development

### 1. Start Redis Locally
You can start a local Redis instance using Docker:
```bash
docker run -p 6379:6379 -d redis:7
```

### 2. Run Backend
Navigate to the `backend` directory, set up your virtual environment, and install dependencies:
```bash
cd backend
cp .env.example .env
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate

pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8080
```

### 3. Usage Examples

**Create a session:**
```bash
curl -X POST localhost:8080/admin/session/create \
  -H "Content-Type: application/json" \
  -d '{"session_id":"replay_demo_1"}'
```

**Call a tool:**
```bash
curl -X POST localhost:8080/tools/get_race_context \
  -H "Content-Type: application/json" \
  -d '{"session_id":"replay_demo_1"}'
```

### 4. Running Tests
Run the pytest suite:
```bash
pytest tests/
```
