from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db_session
from backend.deps import get_current_user, require_admin
from backend.models import Employee
from backend.schemas import PreviewRequestIn, PreviewResponse, ScheduleRequestListItem, ScheduleRequestOut, ShiftAssignIn, ShiftsResponse, StructuredRequestIn
from backend.services.scheduler_service import SchedulerService

router = APIRouter(prefix="/schedule", tags=["schedule"])
service = SchedulerService()


@router.post("/request", response_model=ScheduleRequestOut)
async def create_schedule_request(
    payload: PreviewRequestIn,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: Employee = Depends(get_current_user),
) -> ScheduleRequestOut:
    return await service.request_unified(
        session=session,
        payload=payload,
        correlation_id=request.state.correlation_id,
        current_user=current_user,
    )


@router.get("/requests", response_model=list[ScheduleRequestListItem])
async def list_schedule_requests(
    session: AsyncSession = Depends(get_db_session),
    current_user: Employee = Depends(get_current_user),
):
    return await service.list_requests(session=session, current_user=current_user)


@router.get("/shifts", response_model=ShiftsResponse)
async def list_shifts(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    employee_id: str | None = None,
    session: AsyncSession = Depends(get_db_session),
    current_user: Employee = Depends(get_current_user),
) -> ShiftsResponse:
    effective_employee_id = employee_id
    if current_user.role != current_user.role.admin:  # type: ignore[attr-defined]
        effective_employee_id = str(current_user.id)
    return await service.list_shifts(
        session=session,
        from_date=from_date,
        to_date=to_date,
        employee_id=effective_employee_id,
    )


@router.post("/preview", response_model=PreviewResponse)
async def preview_schedule_request(
    payload: PreviewRequestIn,
    session: AsyncSession = Depends(get_db_session),
    current_user: Employee = Depends(get_current_user),
) -> PreviewResponse:
    return await service.preview_unified(
        session=session, payload=payload, current_user=current_user
    )


@router.post("/request/structured", response_model=ScheduleRequestOut)
async def create_structured_schedule_request(
    payload: StructuredRequestIn,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: Employee = Depends(get_current_user),
) -> ScheduleRequestOut:
    return await service.process_structured_request(
        session=session,
        payload=payload,
        correlation_id=request.state.correlation_id,
        current_user=current_user,
    )


@router.get("/shifts/{shift_id}/candidates")
async def list_shift_candidates(
    shift_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _: Employee = Depends(require_admin),
):
    return await service.list_candidates(session=session, shift_id=shift_id)


@router.post("/shifts/{shift_id}/assign")
async def assign_shift(
    shift_id: UUID,
    payload: ShiftAssignIn,
    session: AsyncSession = Depends(get_db_session),
    _: Employee = Depends(require_admin),
):
    await service.assign_shift(session=session, shift_id=shift_id, employee_id=payload.employee_id)
    return {"shiftId": str(shift_id), "assignedEmployeeId": str(payload.employee_id)}

