from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    llm_provider: Literal["local", "hosted"] = Field(alias="LLM_PROVIDER")
    ollama_base_url: str = Field(alias="OLLAMA_BASE_URL")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    ollama_model: str = Field(default="llama3:8b", alias="OLLAMA_MODEL")
    llm_parse_timeout_seconds: float = Field(default=60.0, alias="LLM_PARSE_TIMEOUT_SECONDS")
    llm_hosted_timeout_seconds: float = Field(default=10.0, alias="LLM_HOSTED_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(default=2, alias="LLM_MAX_RETRIES")
    dev_mode: bool = Field(default=True, alias="DEV_MODE")
    org_timezone: str = Field(default="America/Toronto", alias="ORG_TIMEZONE")


@lru_cache
def get_settings() -> Settings:
    return Settings()

