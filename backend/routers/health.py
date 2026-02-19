import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db_session, redis_client
from backend.llm.factory import get_llm_provider
from backend.schemas import HealthStatus

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthStatus)
async def health() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/db", response_model=HealthStatus)
async def health_db(session: AsyncSession = Depends(get_db_session)) -> HealthStatus:
    start = time.perf_counter()
    try:
        await session.execute(text("SELECT 1"))
        elapsed = (time.perf_counter() - start) * 1000
        return HealthStatus(status="ok", latency_ms=elapsed)
    except Exception as exc:  # noqa: BLE001
        elapsed = (time.perf_counter() - start) * 1000
        return HealthStatus(status="fail", latency_ms=elapsed, last_error=str(exc))


@router.get("/cache", response_model=HealthStatus)
async def health_cache() -> HealthStatus:
    start = time.perf_counter()
    try:
        await redis_client.ping()
        elapsed = (time.perf_counter() - start) * 1000
        return HealthStatus(status="ok", latency_ms=elapsed)
    except Exception as exc:  # noqa: BLE001
        elapsed = (time.perf_counter() - start) * 1000
        return HealthStatus(status="fail", latency_ms=elapsed, last_error=str(exc))


@router.get("/llm", response_model=HealthStatus)
async def health_llm() -> HealthStatus:
    provider = get_llm_provider()
    return await provider.health_check()

