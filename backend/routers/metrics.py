from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db_session
from backend.deps import require_admin
from backend.models import Employee
from backend.metrics import get_metrics
from backend.schemas import MetricsOut

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_model=MetricsOut)
async def metrics_endpoint(
    since: datetime | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    _: Employee = Depends(require_admin),
) -> MetricsOut:
    return await get_metrics(session, since)

