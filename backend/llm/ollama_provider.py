import json
from typing import Any

import httpx
from pydantic import ValidationError

from backend.config import get_settings
from backend.errors import AppError
from backend.llm.base import LLMProvider
from backend.schemas import ErrorCode, HealthStatus, ParsedExtraction

PROMPT_TEMPLATE = """You must respond with only a single JSON object and nothing else. No explanation, no markdown, no code fence.
Use this exact schema (use null when unknown):
{{"employee_first_name":"string","employee_last_name":"string or null","current_shift_date":"YYYY-MM-DD or null","current_shift_type":"morning or night or null","target_date":"YYYY-MM-DD or null","target_shift_type":"morning or night or null","requested_action":"swap or move or cover or null","reason":"string or null","partner_employee_first_name":"string or null","partner_employee_last_name":"string or null","partner_shift_date":"YYYY-MM-DD or null","partner_shift_type":"morning or night or null"}}
For swap requests: set employee_* to the requester, partner_* to the swap partner, current_shift_* to requester's shift, target_* and partner_shift_* to partner's shift.

User request: {text}

JSON:"""


class OllamaProvider(LLMProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model_name = settings.ollama_model
        self.timeout = settings.llm_parse_timeout_seconds
        self.max_retries = settings.llm_max_retries
        self.provider_name = "ollama"
        self.extraction_version = f"ollama-{self.model_name}-v1"

    async def parse(self, text: str, requester_context: str | None = None) -> ParsedExtraction:
        context_line = ""
        if requester_context:
            context_line = f"\nRequester context: {requester_context}\n"
        prompt = PROMPT_TEMPLATE.format(text=text + context_line)
        payload = {"model": self.model_name, "prompt": prompt, "stream": False}

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                body = response.json()
                msg = body.get("message")
                content = (body.get("response") or (msg.get("content") if isinstance(msg, dict) else None) or "").strip()
                if not content:
                    raise AppError(
                        ErrorCode.extraction_invalid_schema,
                        "Could not understand the request format.",
                        "Ollama returned an empty response.",
                        400,
                    )
                data = self._parse_json(content)
                return ParsedExtraction.model_validate(data)
            except httpx.TimeoutException as exc:
                if attempt >= self.max_retries:
                    raise AppError(
                        ErrorCode.llm_timeout,
                        "The language model timed out. Please retry.",
                        f"Ollama timeout after retries: {exc}",
                        504,
                    ) from exc
            except (json.JSONDecodeError, ValidationError) as exc:
                raise AppError(
                    ErrorCode.extraction_invalid_schema,
                    "Could not understand the request format.",
                    f"Ollama schema parse error: {exc}",
                    400,
                ) from exc
            except httpx.HTTPError as exc:
                if attempt >= self.max_retries:
                    raise AppError(
                        ErrorCode.llm_provider_error,
                        "Provider request failed.",
                        f"Ollama provider error: {exc}",
                        502,
                    ) from exc
        raise AppError(ErrorCode.llm_provider_error, "Provider request failed.", "Unexpected retry exit.", 502)

    async def health_check(self) -> HealthStatus:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return HealthStatus(status="ok")
        except Exception as exc:  # noqa: BLE001
            return HealthStatus(status="fail", last_error=str(exc))

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end >= start:
            cleaned = cleaned[start : end + 1]
        return json.loads(cleaned)

