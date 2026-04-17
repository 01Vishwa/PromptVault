from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    anthropic_api_key: str = ""
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agent_eval"
    otel_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "eval-core"
    judge_service_url: str = "http://localhost:8001"
    metrics_service_url: str = "http://localhost:8002"
    eval_task_timeout: int = 60
    eval_judge_model: str = "claude-haiku-4-5-20251001"
    max_cost_per_run: float = 2.0
    log_level: str = "INFO"
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
