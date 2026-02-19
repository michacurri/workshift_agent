from backend.config import get_settings
from backend.llm.base import LLMProvider
from backend.llm.hosted_provider import HostedProvider
from backend.llm.ollama_provider import OllamaProvider


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "hosted":
        return HostedProvider()
    return OllamaProvider()

