from datetime import UTC, date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import redis_client
from backend.errors import AppError
from backend.models import AuditLog, Employee, EmployeeRole, RequestMetrics, RequestStatus, ScheduleRequest, Shift, ShiftType
from backend.schemas import ApprovalActionOut, ErrorCode, PendingApprovalItem


async def _resolve_employee_from_extraction(
    session: AsyncSession, extraction: dict, first_key: str, last_key: str
) -> Employee | None:
    """Resolve single employee by first/last from extraction dict. Returns None if 0 or 2+ matches."""
    first = (extraction.get(first_key) or "").strip() or None
    last = (extraction.get(last_key) or "").strip() or None
    if not first and not last:
        return None
    if first and last:
        stmt = select(Employee).where(Employee.first_name == first, Employee.last_name == last)
    elif first:
        stmt = select(Employee).where(Employee.first_name == first)
    else:
        stmt = select(Employee).where(Employee.last_name == last)
    result = await session.execute(stmt)
    employees = list(result.scalars().all())
    return employees[0] if len(employees) == 1 else None


class ApprovalService:
    async def list_pending(self, session: AsyncSession, current_user: Employee) -> list[PendingApprovalItem]:
        stmt = select(ScheduleRequest).where(
            ScheduleRequest.status.in_([RequestStatus.pending, RequestStatus.pending_admin])
        )
        rows = await session.execute(stmt)
        items = []
        for request in rows.scalars().all():
            ext = request.validated_extraction
            requested_action = ext.get("requested_action")
            requester = await session.get(Employee, request.requester_employee_id) if getattr(request, "requester_employee_id", None) else await _resolve_employee_from_extraction(
                session, ext, "employee_first_name", "employee_last_name"
            )
            partner = None
            if getattr(request, "partner_employee_id", None):
                partner = await session.get(Employee, request.partner_employee_id)
            elif requested_action == "swap":
                partner = await _resolve_employee_from_extraction(
                    session, ext, "partner_employee_first_name", "partner_employee_last_name"
                )
            requester_shift_date = ext.get("current_shift_date")
            requester_shift_type = ext.get("current_shift_type")
            partner_shift_date = ext.get("partner_shift_date") or ext.get("target_date")
            partner_shift_type = ext.get("partner_shift_type") or ext.get("target_shift_type")
            result_summary = None
            if requested_action == "swap" and requester and partner:
                rd = str(requester_shift_date) if requester_shift_date else "?"
                rt = str(requester_shift_type) if requester_shift_type else "?"
                pd = str(partner_shift_date) if partner_shift_date else "?"
                pt = str(partner_shift_type) if partner_shift_type else "?"
                result_summary = f"{requester.full_name} ↔ {partner.full_name}: {requester.full_name}'s {rd} {rt} ↔ {partner.full_name}'s {pd} {pt}"
            if current_user.role != EmployeeRole.admin:
                if not requester or requester.id != current_user.id:
                    continue
            urgent = False
            shift_date_val: date | None = requester_shift_date
            if shift_date_val is None and getattr(request, "requester_shift_id", None):
                sh = await session.get(Shift, request.requester_shift_id)
                if sh:
                    shift_date_val = sh.date
            if shift_date_val is not None:
                shift_start = datetime.combine(shift_date_val, datetime.min.time(), tzinfo=timezone.utc)
                urgent = shift_start <= datetime.now(timezone.utc) + timedelta(hours=48)
            items.append(
                PendingApprovalItem(
                    requestId=request.id,
                    parsed=ext,
                    submittedAt=request.created_at,
                    requested_action=requested_action,
                    requester_full_name=requester.full_name if requester else None,
                    requester_shift_date=requester_shift_date,
                    requester_shift_type=str(requester_shift_type) if requester_shift_type is not None else None,
                    partner_full_name=partner.full_name if partner else None,
                    partner_shift_date=partner_shift_date,
                    partner_shift_type=str(partner_shift_type) if partner_shift_type is not None else None,
                    result_summary=result_summary,
                    urgent=urgent,
                )
            )
        items.sort(key=lambda x: (not x.urgent, x.submittedAt))
        return items

    async def approve(self, session: AsyncSession, request_id: UUID, correlation_id: str) -> ApprovalActionOut:
        request = await self._update_status_if_pending(session, request_id, RequestStatus.approved)
        extraction = request.validated_extraction
        requested_action = extraction.get("requested_action", "move")
        employee = await session.get(Employee, request.requester_employee_id) if getattr(request, "requester_employee_id", None) else await _resolve_employee_from_extraction(
            session, extraction, "employee_first_name", "employee_last_name"
        )
        if not employee:
            raise AppError(
                ErrorCode.rule_employee_not_found,
                "Employee no longer exists.",
                f"Employee missing during approval for request {request_id}",
                409,
            )

        if requested_action == "swap":
            partner = await session.get(Employee, request.partner_employee_id) if getattr(request, "partner_employee_id", None) else await _resolve_employee_from_extraction(
                session, extraction, "partner_employee_first_name", "partner_employee_last_name"
            )
            if not partner:
                raise AppError(
                    ErrorCode.rule_employee_not_found,
                    "Swap partner no longer exists.",
                    f"Partner missing during approval for request {request_id}",
                    409,
                )
            shift_requester = await session.get(Shift, request.requester_shift_id) if getattr(request, "requester_shift_id", None) else None
            shift_partner = await session.get(Shift, request.partner_shift_id) if getattr(request, "partner_shift_id", None) else None
            if not shift_requester or not shift_partner:
                current_date = extraction.get("current_shift_date")
                current_type = extraction.get("current_shift_type")
                target_date = date.fromisoformat(extraction["target_date"])
                target_shift_type = ShiftType(extraction["target_shift_type"])
                if not current_date or not current_type:
                    raise AppError(
                        ErrorCode.validation_error,
                        "Swap request missing requester shift.",
                        "current_shift_date/type missing for swap",
                        409,
                    )
                current_shift_type = ShiftType(current_type)
                shift_requester = shift_requester or await session.scalar(
                    select(Shift).where(
                        and_(Shift.date == current_date, Shift.type == current_shift_type)
                    )
                )
                shift_partner = shift_partner or await session.scalar(
                    select(Shift).where(
                        and_(Shift.date == target_date, Shift.type == target_shift_type)
                    )
                )
            if not shift_requester or not shift_partner:
                raise AppError(
                    ErrorCode.validation_error,
                    "One or both shifts missing for swap.",
                    "Shift not found for swap",
                    409,
                )
            shift_requester.assigned_employee_id = partner.id
            shift_partner.assigned_employee_id = employee.id
        else:
            target_date = date.fromisoformat(extraction["target_date"])
            target_shift_type = ShiftType(extraction["target_shift_type"])
            shift = await session.scalar(
                select(Shift).where(
                    and_(
                        Shift.date == target_date,
                        Shift.type == target_shift_type,
                    )
                )
            )
            if shift:
                shift.assigned_employee_id = employee.id
            else:
                shift = Shift(
                    date=target_date,
                    type=target_shift_type,
                    required_skills={"skills": []},
                    assigned_employee_id=employee.id,
                )
                session.add(shift)

        metrics = await session.get(RequestMetrics, request_id)
        if metrics:
            metrics.approved_at = datetime.now(UTC)

        session.add(
            AuditLog(
                action="approval.approved",
                meta={"request_id": str(request_id), "correlation_id": correlation_id},
            )
        )
        await redis_client.delete(f"approval:{request_id}")
        await session.commit()
        return ApprovalActionOut(requestId=request_id, status=RequestStatus.approved.value, correlationId=correlation_id)

    async def reject(self, session: AsyncSession, request_id: UUID, correlation_id: str) -> ApprovalActionOut:
        await self._update_status_if_pending(session, request_id, RequestStatus.rejected)
        metrics = await session.get(RequestMetrics, request_id)
        if metrics:
            metrics.rejected_at = datetime.now(UTC)
        session.add(
            AuditLog(
                action="approval.rejected",
                meta={"request_id": str(request_id), "correlation_id": correlation_id},
            )
        )
        await redis_client.delete(f"approval:{request_id}")
        await session.commit()
        return ApprovalActionOut(requestId=request_id, status=RequestStatus.rejected.value, correlationId=correlation_id)

    async def _update_status_if_pending(
        self, session: AsyncSession, request_id: UUID, status: RequestStatus
    ) -> ScheduleRequest:
        stmt = (
            update(ScheduleRequest)
            .where(and_(ScheduleRequest.id == request_id, ScheduleRequest.status.in_([RequestStatus.pending, RequestStatus.pending_admin])))
            .values(status=status)
            .returning(ScheduleRequest)
        )
        result = await session.execute(stmt)
        request = result.scalars().first()
        if request is None:
            raise AppError(
                ErrorCode.approval_not_pending,
                "This request is no longer pending.",
                f"Request {request_id} is already acted on or missing.",
                409,
            )
        return request

