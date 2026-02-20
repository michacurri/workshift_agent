"""Minimal real integration test: API health smoke (replaces placeholder)."""
import pytest


@pytest.mark.integration
async def test_health_returns_200_with_status(http_client):
    """GET /health returns 200 and JSON with status (API is up)."""
    r = await http_client.get("/health")
    assert r.status_code == 200, r.text
    assert "status" in r.json()
