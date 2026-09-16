from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ambis.in API"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://postgres:root@127.0.0.1:5432/ambisin_db"
    redis_url: str = "redis://localhost:6379"

    # JWT & Auth
    secret_key: str = "ambis-in-secret-key-change-in-production-2024"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # AI Integration — 9router (OpenAI-compatible proxy), not Gemini.
    # See Decisions/2026-09-15 - LLM provider adalah 9router, bukan Gemini (vault).
    # Placeholders only — fill real values in .env, see .env.example.
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model_grading: str = "cc/PLACEHOLDER_MODEL"
    llm_model_diagnosis: str = "cc/PLACEHOLDER_MODEL"

    # Embeddings — same 9router instance/credentials as above (llm_base_url/llm_api_key),
    # just a different endpoint (/embeddings) and model. Confirmed working via direct
    # testing: gemini-embedding-001, truncated to 768 dims via the `dimensions` param to
    # match curriculum_chunks.embedding's vector(768) column with no migration needed.
    # See Decisions/2026-09-16 - Embedding model gemini-embedding-001 via 9router (vault).
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
