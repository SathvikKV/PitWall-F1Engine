# PitWall-F1Engine 🏎️

**PitWall Live** is a real-time AI-powered Race Engineer dashboard tailored for Formula 1 strategy. Built for the Google Cloud Hackathon, it utilizes the **Gemini Live API** to provide an interactive, multimodal voice agent that understands live race data, predicts strategic outcomes, and can act as an educational F1 tutor natively integrated into the command center.

## 🏆 Hackathon Project Description

### 🌟 What we built (Live Agent)
PitWall transforms the passive F1 fan experience into an interactive one. We built a Next-Generation AI Agent focused on **Real-time Interaction (Audio)**. 
Instead of just looking at spreadsheets of telemetry, users can talk natively to their "AI Race Engineer" through a voice interface that gracefully handles interruptions. 

### 🔧 Core Features & Functionality
- **Multimodal Voice Agent**: Speak directly to the dashboard using your microphone. The agent leverages the **Gemini Live API** to have fluid, interruptible, low-latency conversations.
- **Real-time Track Map**: A live 2D SVG track map that plots driver positions using live `(x, y)` telemetry data.
- **Dynamic Toolkit**: The AI can execute tools on behalf of the user:
  - `project_pit_rejoin`: Calculates where a driver will land on track if they pit right now.
  - `estimate_undercut`: Evaluates if a driver can pull off an undercut strategy.
  - `recommend_strategy`: Analyzes tire age, intervals, and pace to recommend pitting or staying out.
  - `query_wikipedia`: Pulls F1 histories, definitions (like "What is DRS?"), and rules directly from Wikipedia as an educational tutor.
- **Context-Aware Sessions**: The Agent automatically knows if it's looking at a Practice, Qualifying, or Race session and restricts strategy advice appropriately.

### 🛠️ Technologies & Google Cloud Integration
- **Google Cloud Services Used**:
  - **Gemini Live API**: Powers the core multimodal, interruptible audio interaction. (via Google GenAI SDK).
  - **Cloud Run**: Fully serverless hosting for both the React Frontend and FastAPI Backend containers.
  - **Memorystore (Redis)**: High-speed caching for incoming live F1 telemetry.
  - **Firestore**: Serverless NoSQL document database for auditing AI tool usage and logging session state.
  - **Secret Manager**: Securely stores the `GEMINI_API_KEY`.
  - **Cloud Storage (GCS)**: Stores raw NDJSON telemetry replays.
- **Frontend**: Next.js (React 19), Tailwind CSS, ShadCN UI.
- **Backend**: Python, FastAPI.
- **Data Sources**:
  - **FastF1 / OpenF1**: Public APIs for acquiring official Formula 1 timing, telemetry, and track status data.
  - **Wikipedia API**: Text extracts for F1 historical context and rules.

### 🧠 Findings and Learnings
- **Tool Bindings with Live Audio**: Binding JSON schemas to an audio-first agent requires aggressive prompting to ensure the model doesn't "read out" raw tool JSON (like long timestamps or messy coordinates) but instead parses it conversationally.
- **Handling High-Frequency Telemetry**: F1 telemetry comes in fast. Using a dedicated Redis instance was critical; otherwise, the Python backend couldn't process the math for undercut projections quickly enough while simultaneously maintaining the WebRTC/WebSocket audio stream with Gemini.

---

## 🏗️ Architecture Diagram

Below is the high-level architecture showing how the Frontend, Backend, Google Cloud services, and the Gemini Live API interact natively.
*(For a raw file view, see `architecture.md`)*

```mermaid
graph TD
    %% Users
    Client[Web Browser Client]

    %% Frontend Service
    subgraph Frontend [Next.js Web Frontend]
        UI[PitWall UI - React 19]
    end

    %% Backend Service
    subgraph Backend [FastAPI Backend Service]
        API[REST & WebSockets API]
        Agent[Gemini Live Agent]
        LiveClient[OpenF1/FastF1 Data Client]
        Tools[Tool Registry<br/>(Stats, Map, Strategy)]
    end

    %% Cloud Infrastructure
    subgraph GCP [Google Cloud Platform]
        CloudRunWeb[Cloud Run<br/>(Frontend Container)]
        CloudRunAPI[Cloud Run<br/>(Backend Container)]
        Redis[(Memorystore Redis<br/>Session Cache)]
        Firestore[(Firestore DB<br/>Logs & Metadata)]
        SecretManager[Secret Manager<br/>GEMINI_API_KEY]
        Storage[(GCS Bucket<br/>Static Assets)]
    end

    %% External APIs
    GeminiAPI[Google Gemini Live API]
    OpenF1[OpenF1 / FastF1 Public APIs]
    Wikipedia[Wikipedia REST API]

    %% Connections
    Client <-->|HTTPS / WSS| CloudRunWeb
    Client <-->|HTTPS / WSS| CloudRunAPI

    UI <--> CloudRunWeb
    API <--> CloudRunAPI

    CloudRunWeb -.->|Fetch Data| CloudRunAPI

    %% Backend Dependencies
    CloudRunAPI -->|Connect via VPC| Redis
    CloudRunAPI --> Firestore
    CloudRunAPI --> SecretManager
    CloudRunAPI --> Storage

    %% LLM & External Integrations
    Agent <-->|Streaming Audio/Multimodal| GeminiAPI
    LiveClient <-->|Fetch live telemetry| OpenF1
    Tools <-->|Query Rules/Stats| Wikipedia
```

---

## 🚀 Cloud Spin-Up Instructions (Reproducibility)

The project includes a fully robust Infrastructure-as-Code (IaC) setup using **Terraform** to deploy to Google Cloud.

Requirements: `gcloud` CLI installed, authenticated, and Docker installed.

### 1. Build and push Docker Images
Set your project ID:
```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"

# Create an artifact registry repository
gcloud artifacts repositories create pitwall-repo \
    --repository-format=docker \
    --location=$REGION \
    --description="Docker repository for PitWall"
```

Build the Backend:
```bash
cd backend
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/pitwall-repo/pitwall-backend:latest
cd ..
```

Build the Frontend:
```bash
cd web
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/pitwall-repo/pitwall-web:latest
cd ..
```

### 2. Provision Infrastructure via Terraform
Navigate to the `infra` directory.

```bash
cd infra
```

Copy the example variables file:
```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your specifics:
```hcl
project_id     = "your-gcp-project-id"
region         = "us-central1"
gemini_api_key = "AIzaSy..." # Your Gemini API key here
backend_image  = "us-central1-docker.pkg.dev/your-gcp-project-id/pitwall-repo/pitwall-backend:latest"
web_image      = "us-central1-docker.pkg.dev/your-gcp-project-id/pitwall-repo/pitwall-web:latest"
```

Deploy the stack! This will automatically enable all necessary Google Cloud APIs, create the Secret Manager secrets, provision the Redis cache on a Serverless VPC connector, stand up the Firestore database, and deploy the Cloud Run containers.

```bash
terraform init
terraform plan
terraform apply
```

Upon successful apply, Terraform will output the public URL of the Frontend Cloud Run service!

---

## 💻 Local Testing

If you'd prefer to test locally without deploying to GCP, refer to the local scripts:
👉 **[LOCAL_SETUP.md](./LOCAL_SETUP.md)**

```bash
# Requires Docker running for local Redis
./run_local.bat
```