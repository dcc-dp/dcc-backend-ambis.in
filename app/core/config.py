from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ambis.in API"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://postgres:root@127.0.0.1:5432/ambisin_db"
    redis_url: str = "redis://localhost:6379"

    # Database Pool Settings (VPS 4 Core, 4 GB RAM Guardrails)
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    # JWT & Auth
    secret_key: str = "ambis-in-secret-key-change-in-production-2024"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # AI Integration (future)
    openai_api_key: str = ""
    ai_model: str = "gpt-4o"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
