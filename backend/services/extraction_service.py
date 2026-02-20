from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.errors import AppError
from backend.llm.factory import get_llm_provider
from backend.models import Employee, ExtractionVersion, Shift
from backend.schemas import (
    ErrorCode,
    ExtractionResult,
    NeedsInputItem,
    ParsedExtraction,
    RequestedActionEnum,
    ShiftTypeEnum,
    ValidatedExtraction,
)
from backend.time_utils import org_today


SCHEDULE_WINDOW_DAYS = 30


def _next_occurrence(today: date) -> date:
    return today + timedelta(days=1)


def _is_date_in_window(d: date | None, today: date) -> bool:
    """True if d is within [today, today + SCHEDULE_WINDOW_DAYS] (shifts are only future, max 30 days)."""
    if d is None:
        return False
    return today <= d <= today + timedelta(days=SCHEDULE_WINDOW_DAYS)


def _normalize_parsed_dates(parsed: ParsedExtraction, today: date) -> None:
    """Set parsed target_date and current_shift_date to None when outside valid window."""
    if parsed.target_date is not None and not _is_date_in_window(parsed.target_date, today):
        parsed.target_date = None
    if parsed.current_shift_date is not None and not _is_date_in_window(parsed.current_shift_date, today):
        parsed.current_shift_date = None


class ExtractionService:
    def __init__(self) -> None:
        self.provider = get_llm_provider()

    def _build_requester_context(self, current_user: Employee) -> str:
        # Never include stable identifiers (UUIDs) in LLM context.
        # For hosted providers, minimize even further.
        if self.provider.provider_name == "hosted":
            return "Interpret 'my shift', 'I', and 'me' as the requester."
        return (
            f"The requester is {current_user.full_name}. "
            "Interpret 'my shift', 'I', and 'me' as this person."
        )

    async def extract(
        self,
        session: AsyncSession,
        text: str,
        current_user: Employee | None = None,
    ) -> ExtractionResult:
        if current_user is None:
            raise AppError(
                ErrorCode.validation_error,
                "Requester is required.",
                "current_user was null for extraction.",
                400,
            )
        requester_context = self._build_requester_context(current_user)
        today = org_today()
        parsed = await self.provider.parse(text, requester_context=requester_context, reference_date=today)
        _normalize_parsed_dates(parsed, today)
        await self._enforce_parsed_preconditions(session, current_user, parsed)
        validated = self._apply_defaults(parsed, today)
        raw_payload: dict[str, Any] = parsed.model_dump(mode="json")
        await self._ensure_version(session)
        return ExtractionResult(
            parsed=parsed,
            validated=validated,
            raw_payload=raw_payload,
            extraction_version=self.provider.extraction_version,
            provider_name=self.provider.provider_name,
        )

    def _apply_defaults(self, parsed: ParsedExtraction, today: date | None = None) -> ValidatedExtraction:
        if today is None:
            today = org_today()
        _normalize_parsed_dates(parsed, today)
        target_date = parsed.target_date or _next_occurrence(today)

        requested_action = parsed.requested_action or RequestedActionEnum.move
        partner_shift_date = parsed.partner_shift_date
        partner_shift_type = parsed.partner_shift_type
        if requested_action == RequestedActionEnum.swap and (partner_shift_date is None or partner_shift_type is None):
            partner_shift_date = partner_shift_date or target_date
            partner_shift_type = partner_shift_type or parsed.target_shift_type
        # For cover, the shift to be covered is the one on target_date; align current_shift_date so "tomorrow" works.
        if requested_action == RequestedActionEnum.cover:
            parsed.current_shift_date = target_date
            if parsed.current_shift_type is None:
                parsed.current_shift_type = parsed.target_shift_type
        current_shift_date = parsed.current_shift_date
        current_shift_type = parsed.current_shift_type or parsed.target_shift_type
        target_shift_type = parsed.target_shift_type or ShiftTypeEnum.morning
        return ValidatedExtraction(
            employee_first_name=parsed.employee_first_name,
            employee_last_name=parsed.employee_last_name,
            current_shift_date=current_shift_date,
            current_shift_type=current_shift_type or target_shift_type,
            target_date=target_date,
            target_shift_type=target_shift_type,
            requested_action=requested_action,
            reason=parsed.reason,
            partner_employee_first_name=parsed.partner_employee_first_name,
            partner_employee_last_name=parsed.partner_employee_last_name,
            partner_shift_date=partner_shift_date,
            partner_shift_type=partner_shift_type,
        )

    async def parse_lenient(
        self,
        session: AsyncSession,
        text: str,
        current_user: Employee,
    ) -> tuple[ParsedExtraction, list[NeedsInputItem]]:
        """
        Parse text into a draft extraction, returning UI prompts for missing/ambiguous fields.

        This is designed for PREVIEW flows so the UI can guide the user to completion
        without a hard failure.
        """
        requester_context = self._build_requester_context(current_user)
        today = org_today()
        parsed = await self.provider.parse(text, requester_context=requester_context, reference_date=today)

        needs = await self._collect_needs_input(session, current_user, parsed, today)
        return parsed, needs

    async def _collect_needs_input(
        self,
        session: AsyncSession,
        current_user: Employee,
        parsed: ParsedExtraction,
        today: date,
    ) -> list[NeedsInputItem]:
        _normalize_parsed_dates(parsed, today)
        # For cover, the shift to be covered is on target_date; align current_shift_date so "tomorrow" is correct.
        if parsed.requested_action == RequestedActionEnum.cover and parsed.target_date is not None:
            parsed.current_shift_date = parsed.target_date
            if parsed.current_shift_type is None:
                parsed.current_shift_type = parsed.target_shift_type

        # Prefer auto-fill over prompting for requester identity.
        if not (parsed.employee_first_name or "").strip() and not (parsed.employee_last_name or "").strip():
            parsed.employee_first_name = current_user.first_name
            parsed.employee_last_name = current_user.last_name

        needs: list[NeedsInputItem] = []

        # target_date is required for actionable requests; if missing, prompt instead of failing.
        if parsed.target_date is None:
            if parsed.requested_action == RequestedActionEnum.cover and parsed.current_shift_date is not None:
                parsed.target_date = parsed.current_shift_date
            else:
                needs.append(
                    NeedsInputItem(
                        field="target_date",
                        prompt="What date is this request for?",
                    )
                )
                return needs

        # target_shift_type: infer when possible, otherwise prompt.
        if parsed.target_shift_type is None and parsed.target_date is not None:
            result = await session.execute(
                select(Shift).where(
                    Shift.assigned_employee_id == current_user.id,
                    Shift.date == parsed.target_date,
                )
            )
            todays_shifts: list[Shift] = list(result.scalars().all())
            if len(todays_shifts) == 1:
                parsed.target_shift_type = ShiftTypeEnum(todays_shifts[0].type.value)
            elif len(todays_shifts) > 1:
                needs.append(
                    NeedsInputItem(
                        field="target_shift_type",
                        prompt="Which shift type is this for?",
                        options=["morning", "night"],
                    )
                )
            elif len(todays_shifts) == 0:
                needs.append(
                    NeedsInputItem(
                        field="target_date",
                        prompt="No shifts were found on that date. Please pick a different date.",
                    )
                )
        return needs

    async def _enforce_parsed_preconditions(self, session: AsyncSession, current_user: Employee, parsed: ParsedExtraction) -> None:
        if not (parsed.employee_first_name or "").strip() and not (parsed.employee_last_name or "").strip():
            raise AppError(
                ErrorCode.validation_error,
                "Requester first or last name is required.",
                "employee_first_name and employee_last_name both missing.",
                400,
            )
        if parsed.target_date is None:
            if parsed.requested_action == RequestedActionEnum.cover and parsed.current_shift_date is not None:
                parsed.target_date = parsed.current_shift_date
            else: 
                raise AppError(
                    ErrorCode.validation_error,
                    "Target date is required.",
                    "target_date was null.",
                    400,
                )
        if parsed.target_shift_type is None:
            result = await session.execute(select(Shift).where(Shift.assigned_employee_id == current_user.id, Shift.date == parsed.target_date))
            todays_shifts: list[Shift] = list(result.scalars().all())
            if len(todays_shifts) == 1:
                parsed.target_shift_type = ShiftTypeEnum(todays_shifts[0].type.value)
            elif len(todays_shifts) > 1:
                raise AppError(
                    ErrorCode.validation_error,
                    "Multiple shifts found for the same date; please specify the shift type.",
                    "target_shift_type was null/ambiguous.",
                    400,
                )
            elif len(todays_shifts) == 0:
                raise AppError(
                    ErrorCode.validation_error,
                    "No shifts found for the specified date; please specify a different date.",
                    "target_shift_type was null/ambiguous.",
                    400,
                )
    async def _ensure_version(self, session: AsyncSession) -> None:
        version = self.provider.extraction_version
        existing = await session.scalar(select(ExtractionVersion).where(ExtractionVersion.version == version))
        if existing:
            return
        session.add(
            ExtractionVersion(
                version=version,
                model_used=self.provider.model_name,
                prompt_template="schedule_extraction_v1",
            )
        )
        await session.flush()

