"""Integration test isolation fixtures."""

import pytest_asyncio
from sqlalchemy import delete

from backend.db import SessionLocal
from backend.models import AuditLog, RequestMetrics, ScheduleRequest
from backend.scripts.seed_db import seed


@pytest_asyncio.fixture(scope="session", autouse=True)
async def reset_integration_state() -> None:
    """Ensure integration tests start from a deterministic DB state on every run."""
    async with SessionLocal() as session:
        # Clear request-derived state first so seed can safely reset shifts.
        await session.execute(delete(RequestMetrics))
        await session.execute(delete(ScheduleRequest))
        await session.execute(delete(AuditLog))
        await session.commit()

    async with SessionLocal() as session:
        await seed(session)
