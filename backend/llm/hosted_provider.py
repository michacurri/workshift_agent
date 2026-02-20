import json
from datetime import date
from typing import Any

import httpx
from pydantic import ValidationError

from backend.config import get_settings
from backend.errors import AppError
from backend.llm.base import LLMProvider
from backend.schemas import ErrorCode, HealthStatus, ParsedExtraction

PROMPT_TEMPLATE = """Extract schedule request fields and return ONLY valid JSON.
Schema:
{{
  "employee_first_name": "string",
  "employee_last_name": "string or null",
  "current_shift_date": "YYYY-MM-DD or null",
  "current_shift_type": "morning|night|null",
  "target_date": "YYYY-MM-DD or null",
  "target_shift_type": "morning|night|null",
  "requested_action": "swap|move|cover|null",
  "reason": "string or null",
  "partner_employee_first_name": "string or null",
  "partner_employee_last_name": "string or null",
  "partner_shift_date": "YYYY-MM-DD or null",
  "partner_shift_type": "morning|night|null"
}}
For swap: employee_*=requester, partner_*=swap partner, current_shift_*=requester shift, target_* and partner_shift_*=partner shift.
For cover: current_shift_date is the date of the shift to be covered. If the user says "tomorrow" or "my shift tomorrow", set both current_shift_date and target_date to tomorrow (today + 1 day).
{date_context}
User text: {text}
"""


class HostedProvider(LLMProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.openai_base_url.rstrip("/")
        self.api_key = settings.openai_api_key
        self.model_name = settings.openai_model
        self.timeout = settings.llm_hosted_timeout_seconds
        self.max_retries = settings.llm_max_retries
        self.provider_name = "hosted"
        self.extraction_version = f"hosted-{self.model_name}-v1"

    async def parse(
        self,
        text: str,
        requester_context: str | None = None,
        reference_date: date | None = None,
    ) -> ParsedExtraction:
        if not self.api_key:
            raise AppError(
                ErrorCode.llm_provider_error,
                "Hosted LLM provider is not configured.",
                "OPENAI_API_KEY missing for hosted provider.",
                500,
            )
        context_line = ""
        if requester_context:
            context_line = f"\nRequester context: {requester_context}\n"
        date_context = ""
        if reference_date is not None:
            date_context = (
                f"Today's date is {reference_date.isoformat()}. "
                "Valid scheduling window is today through 30 days from today. "
                "For relative dates like 'tomorrow' use today + 1 day. Prefer null if uncertain."
            )
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(date_context=date_context, text=text + context_line)}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
                body = response.json()
                content = body["choices"][0]["message"]["content"]
                data = self._parse_json(content)
                return ParsedExtraction.model_validate(data)
            except httpx.TimeoutException as exc:
                if attempt >= self.max_retries:
                    raise AppError(
                        ErrorCode.llm_timeout,
                        "The hosted language model timed out. Please retry.",
                        f"Hosted timeout after retries: {exc}",
                        504,
                    ) from exc
            except (json.JSONDecodeError, ValidationError, KeyError) as exc:
                raise AppError(
                    ErrorCode.extraction_invalid_schema,
                    "Could not understand the request format.",
                    f"Hosted schema parse error: {exc}",
                    400,
                ) from exc
            except httpx.HTTPError as exc:
                if attempt >= self.max_retries:
                    raise AppError(
                        ErrorCode.llm_provider_error,
                        "Hosted provider request failed.",
                        f"Hosted provider error: {exc}",
                        502,
                    ) from exc
        raise AppError(ErrorCode.llm_provider_error, "Hosted provider request failed.", "Unexpected retry exit.", 502)

    async def health_check(self) -> HealthStatus:
        if not self.api_key:
            return HealthStatus(status="fail", last_error="OPENAI_API_KEY missing")
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/models", headers=headers)
            response.raise_for_status()
            return HealthStatus(status="ok")
        except Exception as exc:  # noqa: BLE001
            return HealthStatus(status="fail", last_error=str(exc))

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        return json.loads(content.strip())

