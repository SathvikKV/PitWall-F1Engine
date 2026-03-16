from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PORT: int = 8080
    LOG_LEVEL: str = "INFO"
    
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    ENV: str = "local"
    GEMINI_API_KEY: str = ""

    # OpenF1 live data (requires sponsor account for live sessions)
    OPENF1_BASE_URL: str = "https://api.openf1.org/v1"
    OPENF1_USERNAME: str = ""
    OPENF1_PASSWORD: str = ""
    OPENF1_POLL_INTERVAL_S: float = 4.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
