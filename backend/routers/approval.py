from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db_session
from backend.deps import get_current_user, require_admin
from backend.models import Employee
from backend.schemas import ApprovalActionOut, PendingApprovalItem
from backend.services.approval_service import ApprovalService

router = APIRouter(prefix="/approval", tags=["approval"])
service = ApprovalService()


@router.get("/pending", response_model=list[PendingApprovalItem])
async def list_pending(
    session: AsyncSession = Depends(get_db_session),
    current_user: Employee = Depends(get_current_user),
) -> list[PendingApprovalItem]:
    return await service.list_pending(session, current_user=current_user)


@router.post("/{request_id}/approve", response_model=ApprovalActionOut)
async def approve_request(
    request_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _: Employee = Depends(require_admin),
) -> ApprovalActionOut:
    return await service.approve(session, request_id, request.state.correlation_id)


@router.post("/{request_id}/reject", response_model=ApprovalActionOut)
async def reject_request(
    request_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _: Employee = Depends(require_admin),
) -> ApprovalActionOut:
    return await service.reject(session, request_id, request.state.correlation_id)

