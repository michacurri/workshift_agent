from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import RequestMetrics, RequestStatus, ScheduleRequest
from backend.schemas import MetricsOut


def _avg_seconds(start_col, end_col):
    return func.avg(func.extract("epoch", end_col - start_col))


async def get_metrics(session: AsyncSession, since: datetime | None = None) -> MetricsOut:
    where_clause = []
    if since:
        where_clause.append(ScheduleRequest.created_at >= since)

    total = await session.scalar(select(func.count(ScheduleRequest.id)).where(*where_clause))
    approved = await session.scalar(
        select(func.count(ScheduleRequest.id)).where(ScheduleRequest.status == RequestStatus.approved, *where_clause)
    )

    avg_processing = await session.scalar(
        select(_avg_seconds(RequestMetrics.submitted_at, RequestMetrics.validated_at))
        .join(ScheduleRequest, ScheduleRequest.id == RequestMetrics.request_id)
        .where(*where_clause)
    )
    parse_time = await session.scalar(
        select(_avg_seconds(RequestMetrics.submitted_at, RequestMetrics.parsed_at))
        .join(ScheduleRequest, ScheduleRequest.id == RequestMetrics.request_id)
        .where(*where_clause)
    )
    validation_time = await session.scalar(
        select(_avg_seconds(RequestMetrics.parsed_at, RequestMetrics.validated_at))
        .join(ScheduleRequest, ScheduleRequest.id == RequestMetrics.request_id)
        .where(*where_clause)
    )
    approval_latency = await session.scalar(
        select(_avg_seconds(RequestMetrics.validated_at, RequestMetrics.approved_at))
        .join(ScheduleRequest, ScheduleRequest.id == RequestMetrics.request_id)
        .where(*where_clause)
    )

    total_requests = int(total or 0)
    approval_rate = float((approved or 0) / total_requests) if total_requests else 0.0
    return MetricsOut(
        total_requests=total_requests,
        approval_rate=approval_rate,
        average_processing_time=float(avg_processing or 0.0),
        parse_time_avg=float(parse_time or 0.0),
        validation_time_avg=float(validation_time or 0.0),
        approval_latency_avg=float(approval_latency or 0.0),
    )

