from abc import ABC, abstractmethod
from datetime import date

from backend.schemas import HealthStatus, ParsedExtraction


class LLMProvider(ABC):
    provider_name: str
    model_name: str
    extraction_version: str

    @abstractmethod
    async def parse(
        self,
        text: str,
        requester_context: str | None = None,
        reference_date: date | None = None,
    ) -> ParsedExtraction:
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        raise NotImplementedError

