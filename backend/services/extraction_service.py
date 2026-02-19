from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.errors import AppError
from backend.llm.factory import get_llm_provider
from backend.models import Employee, ExtractionVersion, Shift
from backend.schemas import ErrorCode, ExtractionResult, ParsedExtraction, RequestedActionEnum, ShiftTypeEnum, ValidatedExtraction


def _next_occurrence(today: date) -> date:
    return today + timedelta(days=1)


class ExtractionService:
    def __init__(self) -> None:
        self.provider = get_llm_provider()

    async def extract(
        self,
        session: AsyncSession,
        text: str,
        current_user: Employee | None = None,
    ) -> ExtractionResult:
        requester_context: str | None = None
        if current_user is not None:
            requester_context = (
                f"The requester is {current_user.full_name} (employee id {current_user.id}). "
                "Interpret 'my shift', 'I', and 'me' as this person."
            )
        else: raise AppError(
            ErrorCode.validation_error,
            "Requester is required.",
            "requester_context was null.",
            400,
        )
        parsed = await self.provider.parse(text, requester_context=requester_context)
        await self._enforce_parsed_preconditions(session, current_user, parsed)
        validated = self._apply_defaults(parsed)
        raw_payload: dict[str, Any] = parsed.model_dump(mode="json")
        await self._ensure_version(session)
        return ExtractionResult(
            parsed=parsed,
            validated=validated,
            raw_payload=raw_payload,
            extraction_version=self.provider.extraction_version,
            provider_name=self.provider.provider_name,
        )

    def _apply_defaults(self, parsed: ParsedExtraction) -> ValidatedExtraction:
        target_date = parsed.target_date or _next_occurrence(datetime.now(UTC).date())

        requested_action = parsed.requested_action or RequestedActionEnum.move
        partner_shift_date = parsed.partner_shift_date
        partner_shift_type = parsed.partner_shift_type
        if requested_action == RequestedActionEnum.swap and (partner_shift_date is None or partner_shift_type is None):
            partner_shift_date = partner_shift_date or target_date
            partner_shift_type = partner_shift_type or parsed.target_shift_type
        return ValidatedExtraction(
            employee_first_name=parsed.employee_first_name,
            employee_last_name=parsed.employee_last_name,
            current_shift_date=parsed.current_shift_date,
            current_shift_type=parsed.current_shift_type,
            target_date=target_date,
            target_shift_type=parsed.target_shift_type,
            requested_action=requested_action,
            reason=parsed.reason,
            partner_employee_first_name=parsed.partner_employee_first_name,
            partner_employee_last_name=parsed.partner_employee_last_name,
            partner_shift_date=partner_shift_date,
            partner_shift_type=partner_shift_type,
        )

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

