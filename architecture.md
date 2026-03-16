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
