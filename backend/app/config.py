"""
Axiom AI Configuration
======================

Centralized configuration management using Pydantic Settings.
Loads from environment variables and .env file.
"""

import sys
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # -------------------------------------------------------------------------
    # NVIDIA NIM Configuration (Primary LLM)
    # -------------------------------------------------------------------------
    nvidia_api_key: str = Field(
        default="",
        description="NVIDIA NIM API key from build.nvidia.com"
    )
    nvidia_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        description="NVIDIA NIM API base URL"
    )
    nvidia_model: str = Field(
        default="nvidia/nemotron-3-nano-30b-a3b",
        description="Default NVIDIA model for reasoning"
    )
    nvidia_embedding_model: str = Field(
        default="nvidia/llama-3_2-nemoretriever-300m-embed-v2",
        description="NVIDIA embedding model"
    )
    
    # -------------------------------------------------------------------------
    # GitHub Models Configuration (Fallback LLM)
    # -------------------------------------------------------------------------
    github_token: str = Field(
        default="",
        description="GitHub personal access token for GitHub Models"
    )
    github_models_url: str = Field(
        default="https://models.inference.ai.azure.com",
        description="GitHub Models API endpoint"
    )
    github_model: str = Field(
        default="gpt-4o",
        description="Default GitHub model for fallback"
    )
    github_fast_model: str = Field(
        default="gpt-4o-mini",
        description="Fast GitHub model for quick operations"
    )
    
    # -------------------------------------------------------------------------
    # Tavily Search Configuration
    # -------------------------------------------------------------------------
    tavily_api_key: str = Field(
        default="",
        description="Tavily API key for web search"
    )
    default_search_results: int = Field(
        default=5,
        description="Default number of search results to return"
    )
    
    # -------------------------------------------------------------------------
    # Application Settings
    # -------------------------------------------------------------------------
    environment: str = Field(
        default="development",
        description="Environment: development, staging, production"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode (must be explicitly enabled)"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # -------------------------------------------------------------------------
    # API Settings
    # -------------------------------------------------------------------------
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host"
    )
    api_port: int = Field(
        default=8000,
        description="API server port"
    )
    cors_origins: str = Field(
        default="http://localhost:3000",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # -------------------------------------------------------------------------
    # Agent Settings
    # -------------------------------------------------------------------------
    max_react_iterations: int = Field(
        default=5,
        description="Maximum iterations for ReACT agent loop"
    )
    max_tool_calls: int = Field(
        default=10,
        description="Maximum tool calls per query"
    )
    observation_truncate_length: int = Field(
        default=1000,
        description="Maximum length for observation text truncation"
    )
    max_sources_in_synthesis: int = Field(
        default=10,
        description="Maximum sources to include in synthesis"
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"
    
    @model_validator(mode='after')
    def validate_production_settings(self) -> 'Settings':
        """Validate settings for production safety."""
        errors = []
        
        # SEC-003: Validate API keys at startup
        if not self.nvidia_api_key and not self.github_token:
            errors.append(
                "CRITICAL: No LLM API key configured. "
                "Set NVIDIA_API_KEY or GITHUB_TOKEN."
            )
        
        if not self.tavily_api_key:
            # Warning only - search can be disabled
            print("WARNING: TAVILY_API_KEY not set. Web search disabled.", file=sys.stderr)
        
        # SEC-004: Validate CORS for production
        if self.is_production:
            if self.debug:
                errors.append(
                    "CRITICAL: DEBUG=True in production environment. "
                    "Set DEBUG=false for production."
                )
            
            if "localhost" in self.cors_origins or "127.0.0.1" in self.cors_origins:
                print(
                    "WARNING: CORS allows localhost in production. "
                    "Review CORS_ORIGINS setting.",
                    file=sys.stderr
                )
        
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            raise ValueError("Configuration validation failed. See errors above.")
        
        return self


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Returns:
        Settings: Application settings singleton
    """
    return Settings()


# Export settings instance for convenience
settings = get_settings()
