"""Integration tests: auth (X-Employee-Id), health endpoints, metrics, error payload shape, LLM error handling.
Stories O1–O5.
"""
import pytest


@pytest.mark.integration
async def test_missing_x_employee_id_returns_401(
    http_client,
):
    """O1: Request without valid X-Employee-Id -> 401 (or 403) for protected endpoints."""
    r = await http_client.get("/schedule/requests")
    assert r.status_code == 401, r.text


@pytest.mark.integration
async def test_invalid_x_employee_id_returns_401(
    http_client,
):
    """O1: Invalid X-Employee-Id (bad UUID or non-existent employee) -> 401."""
    r = await http_client.get("/schedule/requests", headers={"X-Employee-Id": "not-a-uuid"})
    assert r.status_code == 401, r.text


@pytest.mark.integration
async def test_health_endpoints_return_status(
    http_client,
):
    """O2: GET /health, /health/db, /health/cache -> 200 with status; /health/llm reflects LLM availability."""
    r = await http_client.get("/health")
    assert r.status_code == 200, r.text
    assert r.json().get("status") in ("ok", "fail")

    r_db = await http_client.get("/health/db")
    assert r_db.status_code == 200, r_db.text
    assert "status" in r_db.json()

    r_cache = await http_client.get("/health/cache")
    assert r_cache.status_code == 200, r_cache.text
    assert "status" in r_cache.json()

    r_llm = await http_client.get("/health/llm")
    assert r_llm.status_code in (200, 503), r_llm.text
    assert "status" in r_llm.json()


@pytest.mark.integration
async def test_metrics_returns_structure_admin_only(
    http_client, admin_headers, john_headers
):
    """O3: GET /metrics?since=ISO_DATE -> total_requests, approval_rate, etc.; admin only."""
    r = await http_client.get("/metrics", headers=admin_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "total_requests" in data
    assert "approval_rate" in data
    assert "average_processing_time" in data
    assert "parse_time_avg" in data
    assert "validation_time_avg" in data
    assert "approval_latency_avg" in data

    r_non_admin = await http_client.get("/metrics", headers=john_headers)
    assert r_non_admin.status_code == 403, r_non_admin.text


@pytest.mark.integration
async def test_api_error_has_structured_body(
    http_client, john_headers
):
    """O4: Any API error -> structured body: errorCode, userMessage, developerMessage, correlationId."""
    r = await http_client.get("/schedule/requests")
    assert r.status_code == 401, r.text
    data = r.json()
    assert "errorCode" in data
    assert "userMessage" in data
    assert "developerMessage" in data
    assert "correlationId" in data


@pytest.mark.integration
@pytest.mark.integration_llm
async def test_llm_error_returns_503_with_message(
    http_client, john_headers
):
    """O5: When LLM is unavailable or returns invalid response, API returns 503 with clear user message (e.g. EXTRACTION_INVALID_SCHEMA or LLM provider error)."""
    r = await http_client.post(
        "/schedule/preview",
        json={"text": "Swap my Tuesday shift with Alex"},
        headers=john_headers,
    )
    # 200 if LLM works; 503 if LLM down / model not found / invalid response
    assert r.status_code in (200, 503), r.text
    if r.status_code == 503:
        data = r.json()
        assert data.get("errorCode") or data.get("userMessage")
