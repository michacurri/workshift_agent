"""Shared pytest fixtures for unit and integration tests."""
import os
from datetime import date, timedelta
from uuid import UUID

import httpx
import pytest

# Load .env from repo root when running tests locally (e.g. from backend/ or repo root)
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_env = os.path.join(_repo_root, ".env")
if os.path.isfile(_env):
    with open(_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


@pytest.fixture
def api_base_url():
    """Base URL for the running API (integration tests). Default: http://localhost:8000."""
    return os.environ.get("TEST_API_BASE_URL", "http://localhost:8000")


# --- Integration test fixtures (require stack + seed) ---


@pytest.fixture
async def http_client(api_base_url):
    """Async HTTP client for integration tests."""
    async with httpx.AsyncClient(base_url=api_base_url, timeout=60.0) as client:
        yield client


@pytest.fixture
async def employee_ids(http_client):
    """Fetch employees from API and return mapping full_name -> UUID (str). No auth required for GET /employees."""
    r = await http_client.get("/employees")
    assert r.status_code == 200, r.text
    employees = r.json()
    return {e["full_name"]: str(e["id"]) for e in employees}


def _headers(employee_id: str) -> dict:
    return {"X-Employee-Id": employee_id, "Content-Type": "application/json"}


@pytest.fixture
def admin_headers(employee_ids):
    """Headers for admin user (Priya Smith from seed)."""
    eid = employee_ids.get("Priya Smith")
    assert eid, "Seed employee Priya Smith not found; run make seed"
    return _headers(eid)


@pytest.fixture
def john_headers(employee_ids):
    """Headers for John Doe (employee)."""
    eid = employee_ids.get("John Doe")
    assert eid, "Seed employee John Doe not found; run make seed"
    return _headers(eid)


@pytest.fixture
def alex_headers(employee_ids):
    """Headers for Alex Johnson (employee)."""
    eid = employee_ids.get("Alex Johnson")
    assert eid, "Seed employee Alex Johnson not found; run make seed"
    return _headers(eid)


@pytest.fixture
def shift_date_range():
    """Date range covering seed shifts (today through today+10)."""
    today = date.today()
    return (today, today + timedelta(days=10))
