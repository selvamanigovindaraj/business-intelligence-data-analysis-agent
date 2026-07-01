from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # DeepSeek — generation (OpenAI-compatible endpoint)
    deepseek_api_key: str = Field(..., alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field("https://api.deepseek.com", alias="DEEPSEEK_BASE_URL")
    llm_model: str = Field("deepseek-chat", alias="LLM_MODEL")

    # Groq — fast routing / lightweight calls
    groq_api_key: str = Field(..., alias="GROQ_API_KEY")
    router_model: str = Field("llama-3.1-8b-instant", alias="ROUTER_MODEL")

    # Embeddings — Nebius / Qwen3 (OpenAI-compatible endpoint)
    nebius_api_key: str = Field(..., alias="NEBIUS_API_KEY")
    embed_base_url: str = Field(
        "https://api.tokenfactory.nebius.com/v1/", alias="EMBED_BASE_URL"
    )
    embed_model: str = Field("Qwen/Qwen3-Embedding-8B", alias="EMBED_MODEL")
    embed_dim: int = Field(4096, alias="EMBED_DIM")

    # Qdrant
    qdrant_url: str = Field("http://qdrant:6333", alias="QDRANT_URL")
    qdrant_collection_name: str = Field("northwind", alias="QDRANT_COLLECTION_NAME")

    # Tavily
    tavily_api_key: str = Field(..., alias="TAVILY_API_KEY")

    # E2B — sandboxed Python execution for pandas analysis
    e2b_api_key: str = Field(..., alias="E2B_API_KEY")

    # Postgres
    database_url: str = Field(
        "postgresql+asyncpg://agent:agent_secret@postgres:5432/northwind",
        alias="DATABASE_URL",
    )

    # Redis
    redis_url: str = Field("redis://redis:6379/0", alias="REDIS_URL")

    # Phoenix (Arize)
    phoenix_collector_endpoint: str = Field(
        "http://phoenix:4317", alias="PHOENIX_COLLECTOR_ENDPOINT"
    )
    phoenix_project_name: str = Field("bi-agent", alias="PHOENIX_PROJECT_NAME")

    # App
    app_env: str = Field("development", alias="APP_ENV")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"], alias="CORS_ORIGINS"
    )


settings = Settings()  # type: ignore[call-arg]
