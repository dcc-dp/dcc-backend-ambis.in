from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ambis.in API"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ambis"
    redis_url: str = "redis://localhost:6379"

    # AI Integration (future)
    openai_api_key: str = ""
    ai_model: str = "gpt-4o"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
