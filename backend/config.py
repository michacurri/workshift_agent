from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    llm_provider: Literal["local", "hosted"] = Field(alias="LLM_PROVIDER")
    cors_allow_origins: str = Field(
        default="http://localhost:5173,http://localhost:5174",
        alias="CORS_ALLOW_ORIGINS",
        description="Comma-separated list of allowed browser origins (no wildcards in production).",
    )

    # Local LLM (Ollama) settings (required only when LLM_PROVIDER=local)
    ollama_base_url: Optional[str] = Field(default=None, alias="OLLAMA_BASE_URL")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    # Hosted LLM vendor selection (kept inside hosted provider to preserve LLM_PROVIDER=local|hosted contract)
    hosted_llm_vendor: Literal["anthropic", "openai"] = Field(default="anthropic", alias="HOSTED_LLM_VENDOR")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_base_url: str = Field(default="https://api.anthropic.com", alias="ANTHROPIC_BASE_URL")
    anthropic_model: str = Field(default="claude-3-5-sonnet-latest", alias="ANTHROPIC_MODEL")
    anthropic_version: str = Field(default="2023-06-01", alias="ANTHROPIC_VERSION")

    ollama_model: str = Field(default="llama3:8b", alias="OLLAMA_MODEL")
    llm_parse_timeout_seconds: float = Field(default=60.0, alias="LLM_PARSE_TIMEOUT_SECONDS")
    llm_hosted_timeout_seconds: float = Field(default=10.0, alias="LLM_HOSTED_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(default=2, alias="LLM_MAX_RETRIES")
    dev_mode: bool = Field(default=True, alias="DEV_MODE")
    org_timezone: str = Field(default="America/Toronto", alias="ORG_TIMEZONE")


@lru_cache
def get_settings() -> Settings:
    return Settings()

