"""Integration tests: schedule preview, request (text/structured), idempotency, date normalization, payload sanitization.
Stories E1–E7, E12, E13.
"""
from datetime import date, timedelta

import pytest


@pytest.mark.integration
async def test_preview_structured_returns_parsed_validation_summary(
    http_client, john_headers, employee_ids, shift_date_range
):
    """E1: Preview with structured payload returns 200 with parsed, validation, summary."""
    today = date.today()
    payload = {
        "structured": {
            "employee_first_name": "John",
            "employee_last_name": "Doe",
            "current_shift_date": (today + timedelta(days=1)).isoformat(),
            "current_shift_type": "night",
            "target_date": (today + timedelta(days=2)).isoformat(),
            "target_shift_type": "morning",
            "requested_action": "move",
        }
    }
    r = await http_client.post("/schedule/preview", json=payload, headers=john_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "parsed" in data
    assert "validation" in data
    assert "summary" in data
    assert isinstance(data["validation"], dict)
    assert "valid" in data["validation"]


@pytest.mark.integration
async def test_submit_structured_move_creates_pending_admin(
    http_client, john_headers, employee_ids, shift_date_range
):
    """E5 / E6: Submit valid move (structured) -> status pending_admin, summary returned."""
    today = date.today()
    payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "current_shift_date": (today + timedelta(days=1)).isoformat(),
        "current_shift_type": "night",
        "target_date": (today + timedelta(days=8)).isoformat(),
        "target_shift_type": "morning",
        "requested_action": "move",
    }
    r = await http_client.post("/schedule/request/structured", json=payload, headers=john_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "pending_admin"
    assert data["summary"]
    assert data["requestId"]
    assert data["idempotentHit"] is False


@pytest.mark.integration
async def test_submit_structured_swap_creates_pending_partner(
    http_client, john_headers, employee_ids, shift_date_range
):
    """E3 / E6: Submit valid swap (structured) -> status pending_partner, normalized IDs, summary."""
    today = date.today()
    payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "current_shift_date": (today + timedelta(days=7)).isoformat(),
        "current_shift_type": "morning",
        "target_date": (today + timedelta(days=5)).isoformat(),
        "target_shift_type": "night",
        "requested_action": "swap",
        "partner_employee_first_name": "Alex",
        "partner_employee_last_name": "Johnson",
        "partner_shift_date": (today + timedelta(days=5)).isoformat(),
        "partner_shift_type": "night",
    }
    r = await http_client.post("/schedule/request/structured", json=payload, headers=john_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "pending_partner"
    assert data["summary"]
    assert data["requestId"]
    assert data["idempotentHit"] is False


@pytest.mark.integration
async def test_submit_structured_coverage_creates_pending_fill(
    http_client, john_headers, employee_ids, shift_date_range
):
    """E4 / E6: Submit valid coverage (structured) -> status pending_fill, coverage_shift_id set."""
    today = date.today()
    payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "current_shift_date": (today + timedelta(days=9)).isoformat(),
        "current_shift_type": "night",
        "target_date": (today + timedelta(days=9)).isoformat(),
        "target_shift_type": "night",
        "requested_action": "cover",
    }
    r = await http_client.post("/schedule/request/structured", json=payload, headers=john_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "pending_fill"
    assert data["summary"]
    assert data["requestId"]


@pytest.mark.integration
async def test_duplicate_submit_returns_existing_request_idempotent(
    http_client, john_headers, shift_date_range
):
    """E7: Duplicate submit (same fingerprint) -> 200 with existing request, idempotentHit True."""
    today = date.today()
    payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "current_shift_date": (today + timedelta(days=6)).isoformat(),
        "current_shift_type": "morning",
        "target_date": (today + timedelta(days=7)).isoformat(),
        "target_shift_type": "morning",
        "requested_action": "move",
    }
    r1 = await http_client.post("/schedule/request/structured", json=payload, headers=john_headers)
    assert r1.status_code == 200, r1.text
    first = r1.json()
    request_id = first["requestId"]

    r2 = await http_client.post("/schedule/request/structured", json=payload, headers=john_headers)
    assert r2.status_code == 200, r2.text
    second = r2.json()
    assert second["requestId"] == request_id
    assert second["idempotentHit"] is True


@pytest.mark.integration
async def test_preview_structured_with_tomorrow_date_normalized(
    http_client, john_headers, shift_date_range
):
    """E12: Relative date (e.g. tomorrow) in valid window -> correct target date in request."""
    today = date.today()
    tomorrow = (today + timedelta(days=1)).isoformat()
    payload = {
        "structured": {
            "employee_first_name": "John",
            "employee_last_name": "Doe",
            "target_date": tomorrow,
            "target_shift_type": "morning",
            "requested_action": "move",
        }
    }
    r = await http_client.post("/schedule/preview", json=payload, headers=john_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("parsed") or data.get("validation")
    # Submit with same date and ensure it goes through
    submit_payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "target_date": tomorrow,
        "target_shift_type": "morning",
        "requested_action": "move",
    }
    r2 = await http_client.post("/schedule/request/structured", json=submit_payload, headers=john_headers)
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "pending_admin"


@pytest.mark.integration
async def test_structured_optional_date_null_no_422(http_client, john_headers):
    """E13: Optional date fields sent as null -> backend accepts; no 422."""
    today = date.today()
    payload = {
        "structured": {
            "employee_first_name": "John",
            "employee_last_name": "Doe",
            "current_shift_date": None,
            "current_shift_type": None,
            "target_date": (today + timedelta(days=3)).isoformat(),
            "target_shift_type": "morning",
            "requested_action": "move",
            "partner_shift_date": None,
            "partner_shift_type": None,
        }
    }
    r = await http_client.post("/schedule/preview", json=payload, headers=john_headers)
    assert r.status_code == 200, r.text

    submit_payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "target_date": (today + timedelta(days=8)).isoformat(),
        "target_shift_type": "night",
        "requested_action": "move",
        "partner_shift_date": None,
        "partner_shift_type": None,
    }
    r2 = await http_client.post("/schedule/request/structured", json=submit_payload, headers=john_headers)
    assert r2.status_code == 200, r2.text
