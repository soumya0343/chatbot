from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://chatbot:chatbot@localhost:5432/chatbot"
    sync_database_url: str = "postgresql://chatbot:chatbot@localhost:5432/chatbot"
    redis_url: str = "redis://localhost:6379"
    presidio_url: str = "http://localhost:8080"
    presidio_enabled: bool = True

    # When true, the api process also runs the Redis-Streams ingestion consumer
    # in-process (no separate worker). Used for single-service hosted deploys.
    enable_inline_ingestion: bool = False

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    sarvam_api_key: str = ""
    groq_api_key: str = ""

    environment: str = "production"

    redis_stream_key: str = "llm-inference-logs"


settings = Settings()
