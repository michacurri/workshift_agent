from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db_session
from backend.deps import get_current_user
from backend.models import Employee
from backend.schemas import PartnerPendingItem
from backend.services.partner_service import PartnerService

router = APIRouter(prefix="/partner", tags=["partner"])
service = PartnerService()


@router.get("/pending", response_model=list[PartnerPendingItem])
async def list_partner_pending(
    session: AsyncSession = Depends(get_db_session),
    current_user: Employee = Depends(get_current_user),
) -> list[PartnerPendingItem]:
    return await service.list_pending(session, current_user=current_user)


@router.post("/{request_id}/accept")
async def partner_accept(
    request_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: Employee = Depends(get_current_user),
) -> dict:
    await service.accept(session, request_id, current_user)
    return {"requestId": str(request_id), "status": "pending_admin"}


@router.post("/{request_id}/reject")
async def partner_reject(
    request_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: Employee = Depends(get_current_user),
) -> dict:
    await service.reject(session, request_id, current_user)
    return {"requestId": str(request_id), "status": "partner_rejected"}
