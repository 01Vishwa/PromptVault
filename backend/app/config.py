# backend/app/config.py
"""
PromptVault configuration — all values from environment variables.
No hardcoded secrets, URLs, or credentials.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Core ──────────────────────────────────────────────────────────────
    APP_NAME: str = "promptvault"
    ENV: str = Field(default="development")
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ALLOWED_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # ── Supabase ──────────────────────────────────────────────────────────
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(..., description="Supabase anon/public key")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., description="Supabase service role key (server only)")
    SUPABASE_JWT_SECRET: str = Field(..., description="Supabase JWT secret for token validation")

    # ── LLM Provider Keys (server-side only, never exposed) ──────────────
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    GOOGLE_API_KEY: Optional[str] = Field(default=None)

    # ── LiteLLM ───────────────────────────────────────────────────────────
    LITELLM_DROP_PARAMS: bool = True  # silently drop unsupported params per provider

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": True}


@lru_cache()
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
