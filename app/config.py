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

    # Embeddings (OpenAI-compatible — swap base_url for any provider)
    embed_api_key: str = Field(..., alias="EMBED_API_KEY")
    embed_base_url: str = Field("https://api.openai.com/v1", alias="EMBED_BASE_URL")
    embed_model: str = Field("text-embedding-3-small", alias="EMBED_MODEL")

    # Pinecone
    pinecone_api_key: str = Field(..., alias="PINECONE_API_KEY")
    pinecone_index_name: str = Field("ai-agent-index", alias="PINECONE_INDEX_NAME")
    pinecone_environment: str = Field("us-east-1-aws", alias="PINECONE_ENVIRONMENT")

    # Tavily
    tavily_api_key: str = Field(..., alias="TAVILY_API_KEY")

    # Postgres
    database_url: str = Field(
        "postgresql+asyncpg://agent:agent_secret@postgres:5432/agent_db",
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
