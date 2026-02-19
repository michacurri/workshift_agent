from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.errors import AppError
from backend.models import Employee, RequestStatus, ScheduleRequest, Shift
from backend.schemas import ErrorCode, PartnerPendingItem


def _week_range(d: date) -> tuple[date, date]:
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)


class PartnerService:
    async def list_pending(self, session: AsyncSession, current_user: Employee) -> list[PartnerPendingItem]:
        stmt = (
            select(ScheduleRequest)
            .where(
                ScheduleRequest.status == RequestStatus.pending_partner,
                ScheduleRequest.partner_employee_id == current_user.id,
            )
        )
        result = await session.execute(stmt)
        requests = result.scalars().all()
        items = []
        for req in requests:
            ext = req.validated_extraction
            requester = await session.get(Employee, req.requester_employee_id) if getattr(req, "requester_employee_id", None) else None
            summary = _summary_from_extraction(ext, requester)
            requester_shift_date = ext.get("current_shift_date")
            requester_shift_type = ext.get("current_shift_type")
            partner_shift_date = ext.get("partner_shift_date") or ext.get("target_date")
            partner_shift_type = ext.get("partner_shift_type") or ext.get("target_shift_type")
            workload = None
            if partner_shift_date:
                try:
                    pd = partner_shift_date if isinstance(partner_shift_date, date) else date.fromisoformat(str(partner_shift_date))
                    w_start, w_end = _week_range(pd)
                    count_stmt = select(Shift).where(
                        and_(
                            Shift.date >= w_start,
                            Shift.date <= w_end,
                            Shift.assigned_employee_id == current_user.id,
                        )
                    )
                    count_result = await session.execute(count_stmt)
                    workload = len(count_result.scalars().all())
                except (TypeError, ValueError):
                    pass
            items.append(
                PartnerPendingItem(
                    requestId=req.id,
                    summary=summary,
                    requester_full_name=requester.full_name if requester else None,
                    requester_shift_date=requester_shift_date,
                    requester_shift_type=str(requester_shift_type) if requester_shift_type is not None else None,
                    partner_shift_date=partner_shift_date,
                    partner_shift_type=str(partner_shift_type) if partner_shift_type is not None else None,
                    submittedAt=req.created_at,
                    workload_shifts_this_week=workload,
                )
            )
        return items

    async def accept(self, session: AsyncSession, request_id: UUID, current_user: Employee) -> None:
        req = await self._get_pending_partner_request(session, request_id, current_user)
        req.status = RequestStatus.pending_admin
        await session.commit()

    async def reject(self, session: AsyncSession, request_id: UUID, current_user: Employee) -> None:
        req = await self._get_pending_partner_request(session, request_id, current_user)
        req.status = RequestStatus.partner_rejected
        await session.commit()

    async def _get_pending_partner_request(
        self, session: AsyncSession, request_id: UUID, current_user: Employee
    ) -> ScheduleRequest:
        req = await session.get(ScheduleRequest, request_id)
        if not req:
            raise AppError(
                ErrorCode.validation_error,
                "Request not found.",
                f"ScheduleRequest {request_id} not found.",
                404,
            )
        if req.status != RequestStatus.pending_partner:
            raise AppError(
                ErrorCode.approval_not_pending,
                "This request is not awaiting your consent.",
                f"Request {request_id} status is {req.status}",
                409,
            )
        if getattr(req, "partner_employee_id", None) != current_user.id:
            raise AppError(
                ErrorCode.validation_error,
                "You are not the partner for this request.",
                f"Request {request_id} partner is not current user.",
                403,
            )
        return req


def _summary_from_extraction(ext: dict, requester: Employee | None) -> str:
    req_name = (requester.full_name if requester else "") or " ".join(
        filter(None, [ext.get("employee_first_name"), ext.get("employee_last_name")])
    ) or "Requester"
    partner_name = " ".join(filter(None, [ext.get("partner_employee_first_name"), ext.get("partner_employee_last_name")])) or "you"
    cur = f"{ext.get('current_shift_date')} {ext.get('current_shift_type', '')}"
    part = f"{ext.get('partner_shift_date') or ext.get('target_date')} {ext.get('partner_shift_type', '')}"
    return f"Swap: {req_name}'s {cur} ↔ {partner_name}'s {part}"
