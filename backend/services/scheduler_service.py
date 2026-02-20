import hashlib
import json
import uuid
from datetime import UTC, datetime, date, timedelta

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import redis_client
from backend.errors import AppError
from backend.models import AuditLog, Employee, RequestMetrics, RequestStatus, ScheduleRequest, Shift, ShiftType
from backend.models import EmployeeRole
from backend.schemas import (
    ErrorCode,
    ParsedExtraction,
    PreviewRequestIn,
    PreviewResponse,
    RequestedActionEnum,
    RuleEngineResult,
    ScheduleRequestListItem,
    ScheduleRequestOut,
    ShiftCandidateOut,
    ShiftOut,
    ShiftsResponse,
    StructuredRequestIn,
    ValidatedExtraction,
)
from backend.services.extraction_service import ExtractionService
from backend.services.rule_engine import RuleEngine
from backend.time_utils import org_now, org_tz


class SchedulerService:
    def __init__(self) -> None:
        self.extraction_service = ExtractionService()
        self.rule_engine = RuleEngine()

    async def process_request(
        self,
        session: AsyncSession,
        text: str,
        correlation_id: str,
        current_user: Employee,
    ) -> ScheduleRequestOut:
        submitted_at = datetime.now(UTC)
        extraction = await self.extraction_service.extract(session, text, current_user=current_user)
        parsed_dict = extraction.validated.model_dump(mode="json")
        fingerprint = self._fingerprint(parsed_dict)

        existing = await session.scalar(select(ScheduleRequest).where(ScheduleRequest.fingerprint == fingerprint))
        if existing:
            self._enforce_requester_matches_current_user(existing.validated_extraction, current_user)
            rule_result = await self.rule_engine.validate_request(session, extraction.validated)
            return ScheduleRequestOut(
                requestId=existing.id,
                status=existing.status.value,
                extractionVersion=existing.extraction_version,
                parsed=existing.validated_extraction,
                validation=rule_result,
                approvalId=str(existing.id) if existing.status in (RequestStatus.pending, RequestStatus.pending_admin) else None,
                correlationId=correlation_id,
                idempotentHit=True,
                summary=self._build_summary(existing.validated_extraction, rule_result),
            )

        parsed_at = datetime.now(UTC)
        rule_result = await self.rule_engine.validate_request(session, extraction.validated)
        validated_at = datetime.now(UTC)
        self._enforce_requester_matches_current_user(parsed_dict, current_user)
        status, partner_id, req_shift_id, part_shift_id, cov_shift_id = await self._resolve_normalized_ids_and_status(
            session, extraction.validated, current_user, rule_result.valid
        )
        schedule_request = ScheduleRequest(
            raw_text=text,
            extracted_data=extraction.parsed.model_dump(mode="json"),
            raw_extraction=extraction.raw_payload,
            validated_extraction=parsed_dict,
            extraction_version=extraction.extraction_version,
            fingerprint=fingerprint,
            status=status,
            requester_employee_id=current_user.id,
            partner_employee_id=partner_id,
            requester_shift_id=req_shift_id,
            partner_shift_id=part_shift_id,
            coverage_shift_id=cov_shift_id,
        )
        session.add(schedule_request)
        try:
            await session.flush()
        except IntegrityError as exc:
            await session.rollback()
            existing = await session.scalar(select(ScheduleRequest).where(ScheduleRequest.fingerprint == fingerprint))
            if existing:
                self._enforce_requester_matches_current_user(existing.validated_extraction, current_user)
                rule_result = await self.rule_engine.validate_request(session, extraction.validated)
                return ScheduleRequestOut(
                    requestId=existing.id,
                    status=existing.status.value,
                    extractionVersion=existing.extraction_version,
                    parsed=existing.validated_extraction,
                    validation=rule_result,
                    approvalId=str(existing.id)
                    if existing.status in (RequestStatus.pending, RequestStatus.pending_admin)
                    else None,
                    correlationId=correlation_id,
                    idempotentHit=True,
                    summary=self._build_summary(existing.validated_extraction, rule_result),
                )
            raise exc

        session.add(
            RequestMetrics(
                request_id=schedule_request.id,
                submitted_at=submitted_at,
                parsed_at=parsed_at,
                validated_at=validated_at,
                rejected_at=validated_at if status == RequestStatus.rejected else None,
            )
        )
        session.add(
            AuditLog(
                action="schedule.request.created",
                meta={
                    "request_id": str(schedule_request.id),
                    "status": status.value,
                    "provider": extraction.provider_name,
                    "correlation_id": correlation_id,
                },
            )
        )
        approval_id = None
        if status in (RequestStatus.pending, RequestStatus.pending_admin):
            approval_id = str(schedule_request.id)
            await redis_client.set(f"approval:{approval_id}", approval_id, ex=900)
        await session.commit()
        return ScheduleRequestOut(
            requestId=schedule_request.id,
            status=status.value,
            extractionVersion=extraction.extraction_version,
            parsed=parsed_dict,
            validation=rule_result,
            approvalId=approval_id,
            correlationId=correlation_id,
            idempotentHit=False,
            summary=self._build_summary(parsed_dict, rule_result),
        )

    async def preview_structured(
        self,
        session: AsyncSession,
        payload: StructuredRequestIn,
    ):
        """Validate a structured request without creating a ScheduleRequest."""
        parsed = ParsedExtraction(
            employee_first_name=payload.employee_first_name,
            employee_last_name=payload.employee_last_name,
            current_shift_date=payload.current_shift_date,
            current_shift_type=payload.current_shift_type,
            target_date=payload.target_date,
            target_shift_type=payload.target_shift_type,
            requested_action=payload.requested_action,
            reason=payload.reason,
            partner_employee_first_name=payload.partner_employee_first_name,
            partner_employee_last_name=payload.partner_employee_last_name,
            partner_shift_date=payload.partner_shift_date,
            partner_shift_type=payload.partner_shift_type,
        )
        validated = self.extraction_service._apply_defaults(parsed)
        rule_result = await self.rule_engine.validate_request(session, validated)
        return {
            "parsed": validated.model_dump(mode="json"),
            "validation": rule_result,
        }

    async def preview_unified(
        self,
        session: AsyncSession,
        payload: PreviewRequestIn,
        current_user: Employee | None = None,
    ) -> PreviewResponse:
        """Unified preview: accept text or structured; return parsed, validation, summary."""
        if payload.text and payload.text.strip():
            if current_user is None:
                raise AppError(
                    ErrorCode.validation_error,
                    "Authentication is required for preview.",
                    "current_user was null in preview_unified(text).",
                    401,
                )
            parsed, needs = await self.extraction_service.parse_lenient(
                session=session,
                text=payload.text.strip(),
                current_user=current_user,
            )
            parsed_dict = parsed.model_dump(mode="json")
            if needs:
                rule_result = RuleEngineResult(
                    valid=False,
                    errorCodes=[ErrorCode.validation_error],
                    reason="Additional information required to preview this request.",
                    suggestions=[],
                    validationDetails={"needsInput": [n.model_dump() for n in needs]},
                )
                summary = self._build_summary(parsed_dict, rule_result)
                return PreviewResponse(parsed=parsed_dict, validation=rule_result, summary=summary, needsInput=needs)

            validated = self.extraction_service._apply_defaults(parsed)
            validated_dict = validated.model_dump(mode="json")
            rule_result = await self.rule_engine.validate_request(session, validated)
        else:
            st = payload.structured
            parsed = ParsedExtraction(
                employee_first_name=st.employee_first_name,
                employee_last_name=st.employee_last_name,
                current_shift_date=st.current_shift_date,
                current_shift_type=st.current_shift_type,
                target_date=st.target_date,
                target_shift_type=st.target_shift_type,
                requested_action=st.requested_action,
                reason=st.reason,
                partner_employee_first_name=st.partner_employee_first_name,
                partner_employee_last_name=st.partner_employee_last_name,
                partner_shift_date=st.partner_shift_date,
                partner_shift_type=st.partner_shift_type,
            )
            validated = self.extraction_service._apply_defaults(parsed)
            validated_dict = validated.model_dump(mode="json")
            rule_result = await self.rule_engine.validate_request(session, validated)
        summary = self._build_summary(validated_dict, rule_result)
        return PreviewResponse(parsed=validated_dict, validation=rule_result, summary=summary, needsInput=[])

    async def process_structured_request(
        self,
        session: AsyncSession,
        payload: StructuredRequestIn,
        correlation_id: str,
        current_user: Employee,
    ) -> ScheduleRequestOut:
        parsed = ParsedExtraction(
            employee_first_name=payload.employee_first_name,
            employee_last_name=payload.employee_last_name,
            current_shift_date=payload.current_shift_date,
            current_shift_type=payload.current_shift_type,
            target_date=payload.target_date,
            target_shift_type=payload.target_shift_type,
            requested_action=payload.requested_action,
            reason=payload.reason,
            partner_employee_first_name=payload.partner_employee_first_name,
            partner_employee_last_name=payload.partner_employee_last_name,
            partner_shift_date=payload.partner_shift_date,
            partner_shift_type=payload.partner_shift_type,
        )
        validated = self.extraction_service._apply_defaults(parsed)
        parsed_dict = validated.model_dump(mode="json")
        fingerprint = self._fingerprint(parsed_dict)

        existing = await session.scalar(select(ScheduleRequest).where(ScheduleRequest.fingerprint == fingerprint))
        if existing:
            self._enforce_requester_matches_current_user(existing.validated_extraction, current_user)
            rule_result = await self.rule_engine.validate_request(session, validated)
            return ScheduleRequestOut(
                requestId=existing.id,
                status=existing.status.value,
                extractionVersion=existing.extraction_version,
                parsed=existing.validated_extraction,
                validation=rule_result,
                approvalId=str(existing.id) if existing.status in (RequestStatus.pending, RequestStatus.pending_admin) else None,
                correlationId=correlation_id,
                idempotentHit=True,
                summary=self._build_summary(existing.validated_extraction, rule_result),
            )

        submitted_at = datetime.now(UTC)
        parsed_at = submitted_at
        rule_result = await self.rule_engine.validate_request(session, validated)
        validated_at = datetime.now(UTC)
        self._enforce_requester_matches_current_user(parsed_dict, current_user)
        status, partner_id, req_shift_id, part_shift_id, cov_shift_id = await self._resolve_normalized_ids_and_status(
            session, validated, current_user, rule_result.valid
        )
        # Structured requests bypass ExtractionService.extract(); ensure extraction_versions FK target exists.
        await self.extraction_service._ensure_version(session)

        schedule_request = ScheduleRequest(
            raw_text="(structured)",
            extracted_data=parsed.model_dump(mode="json"),
            raw_extraction=parsed.model_dump(mode="json"),
            validated_extraction=parsed_dict,
            extraction_version=self.extraction_service.provider.extraction_version,
            fingerprint=fingerprint,
            status=status,
            requester_employee_id=current_user.id,
            partner_employee_id=partner_id,
            requester_shift_id=req_shift_id,
            partner_shift_id=part_shift_id,
            coverage_shift_id=cov_shift_id,
        )
        session.add(schedule_request)
        try:
            await session.flush()
        except IntegrityError as exc:
            await session.rollback()
            existing = await session.scalar(select(ScheduleRequest).where(ScheduleRequest.fingerprint == fingerprint))
            if existing:
                self._enforce_requester_matches_current_user(existing.validated_extraction, current_user)
                rule_result = await self.rule_engine.validate_request(session, validated)
                return ScheduleRequestOut(
                    requestId=existing.id,
                    status=existing.status.value,
                    extractionVersion=existing.extraction_version,
                    parsed=existing.validated_extraction,
                    validation=rule_result,
                    approvalId=str(existing.id)
                    if existing.status in (RequestStatus.pending, RequestStatus.pending_admin)
                    else None,
                    correlationId=correlation_id,
                    idempotentHit=True,
                    summary=self._build_summary(existing.validated_extraction, rule_result),
                )
            raise exc

        session.add(
            RequestMetrics(
                request_id=schedule_request.id,
                submitted_at=submitted_at,
                parsed_at=parsed_at,
                validated_at=validated_at,
                rejected_at=validated_at if status == RequestStatus.rejected else None,
            )
        )

        session.add(
            AuditLog(
                action="schedule.request.structured_created",
                meta={
                    "request_id": str(schedule_request.id),
                    "status": status.value,
                    "provider": self.extraction_service.provider.provider_name,
                    "correlation_id": correlation_id,
                },
            )
        )

        approval_id = None
        if status in (RequestStatus.pending, RequestStatus.pending_admin):
            approval_id = str(schedule_request.id)
            await redis_client.set(f"approval:{approval_id}", approval_id, ex=900)

        await session.commit()
        return ScheduleRequestOut(
            requestId=schedule_request.id,
            status=status.value,
            extractionVersion=self.extraction_service.provider.extraction_version,
            parsed=parsed_dict,
            validation=rule_result,
            approvalId=approval_id,
            correlationId=correlation_id,
            idempotentHit=False,
            summary=self._build_summary(parsed_dict, rule_result),
        )

    async def request_unified(
        self,
        session: AsyncSession,
        payload: PreviewRequestIn,
        correlation_id: str,
        current_user: Employee,
    ) -> ScheduleRequestOut:
        """Unified request: accept text or structured; create request and return with summary."""
        if payload.text and payload.text.strip():
            return await self.process_request(
                session=session,
                text=payload.text.strip(),
                correlation_id=correlation_id,
                current_user=current_user,
            )
        return await self.process_structured_request(
            session=session,
            payload=payload.structured,
            correlation_id=correlation_id,
            current_user=current_user,
        )

    async def list_shifts(
        self,
        session: AsyncSession,
        from_date: date,
        to_date: date,
        employee_id: str | None = None,
    ) -> ShiftsResponse:
        stmt = select(Shift).where(
            and_(
                Shift.date >= from_date,
                Shift.date <= to_date,
            )
        )
        if employee_id:
            stmt = stmt.where(Shift.assigned_employee_id == employee_id)
        result = await session.execute(stmt)
        shifts = result.scalars().all()

        employee_ids = {s.assigned_employee_id for s in shifts if s.assigned_employee_id is not None}
        employees_map: dict[str, Employee] = {}
        if employee_ids:
            employees_result = await session.execute(select(Employee).where(Employee.id.in_(employee_ids)))
            for emp in employees_result.scalars().all():
                employees_map[str(emp.id)] = emp

        items: list[ShiftOut] = []
        for s in shifts:
            assigned_id_str = str(s.assigned_employee_id) if s.assigned_employee_id is not None else None
            emp = employees_map.get(assigned_id_str) if assigned_id_str else None
            items.append(
                ShiftOut(
                    id=s.id,
                    date=s.date,
                    type=s.type.value,
                    required_skills=s.required_skills or {},
                    assigned_employee_id=s.assigned_employee_id,
                    assigned_employee_full_name=emp.full_name if emp else None,
                )
            )
        return ShiftsResponse(shifts=items)

    async def list_candidates(
        self,
        session: AsyncSession,
        shift_id: uuid.UUID,
    ) -> list[ShiftCandidateOut]:
        """List employees eligible to fill this shift (admin use)."""
        shift = await session.get(Shift, shift_id)
        if not shift:
            return []
        pairs = await self.rule_engine.get_eligible_candidates_for_shift(session, shift)
        week_start = shift.date - timedelta(days=shift.date.weekday())
        week_end = week_start + timedelta(days=6)
        out: list[ShiftCandidateOut] = []
        for emp, reason in pairs:
            count_stmt = select(Shift).where(
                and_(
                    Shift.date >= week_start,
                    Shift.date <= week_end,
                    Shift.assigned_employee_id == emp.id,
                )
            )
            count_result = await session.execute(count_stmt)
            shifts_this_week = len(count_result.scalars().all())
            out.append(
                ShiftCandidateOut(
                    employee_id=emp.id,
                    full_name=emp.full_name,
                    reason=reason,
                    shifts_this_week=shifts_this_week,
                )
            )
        return out

    async def assign_shift(
        self,
        session: AsyncSession,
        shift_id: uuid.UUID,
        employee_id: uuid.UUID,
    ) -> None:
        """Assign shift to employee (admin). Optionally mark coverage request as approved."""
        shift = await session.get(Shift, shift_id)
        if not shift:
            raise AppError(
                ErrorCode.validation_error,
                "Shift not found.",
                f"Shift {shift_id} not found.",
                404,
            )
        shift.assigned_employee_id = employee_id
        stmt = select(ScheduleRequest).where(
            ScheduleRequest.coverage_shift_id == shift_id,
            ScheduleRequest.status == RequestStatus.pending_fill,
        )
        cov_result = await session.execute(stmt)
        req = cov_result.scalars().first()
        if req:
            req.status = RequestStatus.approved
        await session.commit()

    async def list_requests(
        self,
        session: AsyncSession,
        current_user: Employee,
    ) -> list[ScheduleRequestListItem]:
        """List requests: employees see own + partner-consent; admins see all."""
        stmt = select(ScheduleRequest)
        if current_user.role != EmployeeRole.admin:
            stmt = stmt.where(
                (ScheduleRequest.requester_employee_id == current_user.id)
                | (ScheduleRequest.partner_employee_id == current_user.id)
            )
        stmt = stmt.order_by(ScheduleRequest.created_at.desc())
        result = await session.execute(stmt)
        rows = result.scalars().all()
        unresolved = {RequestStatus.pending_partner, RequestStatus.pending_admin, RequestStatus.pending_fill, RequestStatus.pending}
        now = org_now()
        cutoff = now + timedelta(hours=48)
        items = []
        for req in rows:
            requester = await session.get(Employee, req.requester_employee_id) if getattr(req, "requester_employee_id", None) else None
            summary = self._build_summary(req.validated_extraction, RuleEngineResult(valid=True, errorCodes=[], reason=None))
            urgent = False
            if req.status in unresolved:
                shift_date: date | None = None
                if getattr(req, "coverage_shift_id", None):
                    sh = await session.get(Shift, req.coverage_shift_id)
                    if sh:
                        shift_date = sh.date
                if shift_date is None and getattr(req, "requester_shift_id", None):
                    sh = await session.get(Shift, req.requester_shift_id)
                    if sh:
                        shift_date = sh.date
                if shift_date is None:
                    ext = req.validated_extraction
                    for key in ("current_shift_date", "target_date", "partner_shift_date"):
                        d = ext.get(key)
                        if d:
                            shift_date = d if isinstance(d, date) else date.fromisoformat(str(d))
                            break
                if shift_date is not None:
                    shift_start = datetime.combine(shift_date, datetime.min.time(), tzinfo=org_tz())
                    urgent = shift_start <= cutoff
            items.append(
                ScheduleRequestListItem(
                    requestId=req.id,
                    status=req.status.value,
                    summary=summary,
                    created_at=req.created_at,
                    requester_full_name=requester.full_name if requester else None,
                    coverage_shift_id=getattr(req, "coverage_shift_id", None),
                    urgent=urgent,
                )
            )
        items.sort(key=lambda x: (not x.urgent, x.created_at), reverse=True)
        return items

    async def _resolve_normalized_ids_and_status(
        self,
        session: AsyncSession,
        validated: ValidatedExtraction,
        current_user: Employee,
        is_valid: bool,
    ) -> tuple[
        RequestStatus,
        type(None) | uuid.UUID,
        type(None) | uuid.UUID,
        type(None) | uuid.UUID,
        type(None) | uuid.UUID,
    ]:
        """Resolve partner and shift IDs; return (status, partner_id, requester_shift_id, partner_shift_id, coverage_shift_id)."""
        if not is_valid:
            return RequestStatus.rejected, None, None, None, None
        action = validated.requested_action or RequestedActionEnum.move
        partner_id: uuid.UUID | None = None
        req_shift_id: uuid.UUID | None = None
        part_shift_id: uuid.UUID | None = None
        cov_shift_id: uuid.UUID | None = None

        if action == RequestedActionEnum.swap:
            partners = await self.rule_engine.resolve_employee(
                session,
                validated.partner_employee_first_name or None,
                validated.partner_employee_last_name or None,
            )
            if len(partners) == 1:
                partner_id = partners[0].id
            if validated.current_shift_date and validated.current_shift_type:
                shift_req = await self._get_shift(
                    session,
                    validated.current_shift_date,
                    ShiftType(validated.current_shift_type.value),
                    assigned_employee_id=current_user.id,
                )
                if shift_req:
                    req_shift_id = shift_req.id
            pd = validated.partner_shift_date or validated.target_date
            pt = validated.partner_shift_type or validated.target_shift_type
            shift_part = await self._get_shift(session, pd, ShiftType(pt.value))
            if shift_part:
                part_shift_id = shift_part.id
            return RequestStatus.pending_partner, partner_id, req_shift_id, part_shift_id, None

        if action == RequestedActionEnum.cover and validated.current_shift_date and validated.current_shift_type:
            shift_cov = await self._get_shift(
                session,
                validated.current_shift_date,
                ShiftType(validated.current_shift_type.value),
                assigned_employee_id=current_user.id,
            )
            if shift_cov is None and validated.target_date and validated.target_shift_type:
                shift_cov = await self._get_shift(
                    session,
                    validated.target_date,
                    ShiftType(validated.target_shift_type.value),
                    assigned_employee_id=current_user.id,
                )
            if shift_cov:
                cov_shift_id = shift_cov.id
                req_shift_id = shift_cov.id
            return RequestStatus.pending_fill, None, req_shift_id, None, cov_shift_id

        return RequestStatus.pending_admin, None, None, None, None

    async def _get_shift(
        self,
        session: AsyncSession,
        shift_date: date,
        shift_type: ShiftType,
        assigned_employee_id: uuid.UUID | None = None,
    ):
        stmt = select(Shift).where(Shift.date == shift_date, Shift.type == shift_type)
        if assigned_employee_id is not None:
            stmt = stmt.where(Shift.assigned_employee_id == assigned_employee_id)
        return await session.scalar(stmt)

    @staticmethod
    def _build_summary(parsed: dict, validation: RuleEngineResult) -> str:
        """Human-readable one-line summary for UI."""
        action = parsed.get("requested_action") or "move"
        req_name = " ".join(filter(None, [parsed.get("employee_first_name"), parsed.get("employee_last_name")])) or "Requester"
        if not parsed.get("target_date"):
            if action == "cover":
                return f"Request coverage for {req_name} (date needed)"
            if action == "swap":
                return f"Swap request for {req_name} (details needed)"
            return f"Move request for {req_name} (date needed)"
        target = f"{parsed.get('target_date')} {parsed.get('target_shift_type', '')}"
        if action == "swap":
            partner_name = " ".join(filter(None, [parsed.get("partner_employee_first_name"), parsed.get("partner_employee_last_name")])) or "Partner"
            cur = f"{parsed.get('current_shift_date')} {parsed.get('current_shift_type', '')}"
            part = f"{parsed.get('partner_shift_date') or parsed.get('target_date')} {parsed.get('partner_shift_type', '')}"
            return f"Swap: {req_name}'s {cur} ↔ {partner_name}'s {part}"
        if action == "cover":
            cur = f"{parsed.get('current_shift_date')} {parsed.get('current_shift_type', '')}"
            return f"Request coverage for {req_name}'s {cur}"
        return f"Move: {req_name} → {target}"

    @staticmethod
    def _fingerprint(parsed: dict) -> str:
        payload = {
            "employee_first_name": parsed["employee_first_name"],
            "employee_last_name": parsed["employee_last_name"],
            "target_date": parsed["target_date"],
            "target_shift_type": parsed["target_shift_type"],
            "requested_action": parsed["requested_action"],
        }
        if parsed.get("requested_action") == "swap":
            payload["partner_employee_first_name"] = parsed.get("partner_employee_first_name")
            payload["partner_employee_last_name"] = parsed.get("partner_employee_last_name")
            payload["current_shift_date"] = str(parsed["current_shift_date"]) if parsed.get("current_shift_date") else None
            payload["current_shift_type"] = parsed.get("current_shift_type")
            payload["partner_shift_date"] = str(parsed["partner_shift_date"]) if parsed.get("partner_shift_date") else None
            payload["partner_shift_type"] = parsed.get("partner_shift_type")
        canonical = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _enforce_requester_matches_current_user(parsed: dict, current_user: Employee) -> None:
        """Ensure the request is for the current user unless they are an admin."""
        if current_user.role == EmployeeRole.admin:
            return
        requester_first = (parsed.get("employee_first_name") or "").strip()
        requester_last = (parsed.get("employee_last_name") or "").strip()
        if not requester_first and not requester_last:
            raise AppError(
                ErrorCode.validation_error,
                "Requester details are missing from the request.",
                "Validated extraction missing employee_first_name/last_name during auth check.",
                400,
            )
        if requester_first != current_user.first_name or (
            requester_last and requester_last != current_user.last_name
        ):
            raise AppError(
                ErrorCode.validation_error,
                "You can only submit requests for yourself unless you are an admin.",
                f"Current user {current_user.id} does not match requester {requester_first} {requester_last}.",
                403,
            )

