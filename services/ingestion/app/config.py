from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://chatbot:chatbot@localhost:5432/chatbot"
    redis_url: str = "redis://localhost:6379"
    redis_stream_key: str = "llm-inference-logs"
    redis_consumer_group: str = "ingestion-workers"
    presidio_url: str = "http://localhost:8080"
    batch_size: int = 50
    batch_timeout_ms: int = 1000
    environment: str = "production"


settings = Settings()
