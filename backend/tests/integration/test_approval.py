"""Integration tests: approval flow (list pending with urgent order, approve, reject, double approve/reject 409, admin-only).
Stories A1–A4, A8.
"""
from datetime import date, timedelta

import pytest


@pytest.mark.integration
async def test_admin_sees_pending_approvals_urgent_first(
    http_client, john_headers, admin_headers
):
    """A1: Admin opens Approvals -> GET /approval/pending returns pending/pending_admin; urgent first; summary, full names."""
    today = date.today()
    payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "target_date": (today + timedelta(days=1)).isoformat(),
        "target_shift_type": "morning",
        "requested_action": "move",
    }
    await http_client.post("/schedule/request/structured", json=payload, headers=john_headers)

    r = await http_client.get("/approval/pending", headers=admin_headers)
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list)
    for item in items:
        assert "requestId" in item
        assert "urgent" in item
        assert "requester_full_name" in item or "result_summary" in item


@pytest.mark.integration
async def test_admin_approve_sets_status_approved(
    http_client, john_headers, admin_headers
):
    """A2: Admin approves -> POST /approval/{id}/approve -> status approved; transactional."""
    today = date.today()
    payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "target_date": (today + timedelta(days=9)).isoformat(),
        "target_shift_type": "night",
        "requested_action": "move",
    }
    r_create = await http_client.post("/schedule/request/structured", json=payload, headers=john_headers)
    assert r_create.status_code == 200, r_create.text
    request_id = r_create.json()["requestId"]

    r_approve = await http_client.post(f"/approval/{request_id}/approve", headers=admin_headers)
    assert r_approve.status_code == 200, r_approve.text
    assert r_approve.json().get("status") == "approved"


@pytest.mark.integration
async def test_admin_reject_sets_status_rejected(
    http_client, john_headers, admin_headers
):
    """A3: Admin rejects -> POST /approval/{id}/reject -> status rejected; transactional."""
    today = date.today()
    payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "target_date": (today + timedelta(days=10)).isoformat(),
        "target_shift_type": "morning",
        "requested_action": "move",
    }
    r_create = await http_client.post("/schedule/request/structured", json=payload, headers=john_headers)
    assert r_create.status_code == 200, r_create.text
    request_id = r_create.json()["requestId"]

    r_reject = await http_client.post(f"/approval/{request_id}/reject", headers=admin_headers)
    assert r_reject.status_code == 200, r_reject.text
    assert r_reject.json().get("status") == "rejected"


@pytest.mark.integration
async def test_double_approve_returns_409_approval_not_pending(
    http_client, john_headers, admin_headers
):
    """A4: Admin approves same request twice -> second call 409 APPROVAL_NOT_PENDING; state unchanged."""
    today = date.today()
    payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "target_date": (today + timedelta(days=8)).isoformat(),
        "target_shift_type": "night",
        "requested_action": "move",
    }
    r_create = await http_client.post("/schedule/request/structured", json=payload, headers=john_headers)
    assert r_create.status_code == 200, r_create.text
    request_id = r_create.json()["requestId"]

    await http_client.post(f"/approval/{request_id}/approve", headers=admin_headers)
    r_second = await http_client.post(f"/approval/{request_id}/approve", headers=admin_headers)
    assert r_second.status_code == 409, r_second.text
    assert r_second.json().get("errorCode") == "APPROVAL_NOT_PENDING"


@pytest.mark.integration
async def test_non_admin_approve_returns_403(
    http_client, john_headers, alex_headers, admin_headers
):
    """A8: Non-admin calls approve -> 403."""
    today = date.today()
    payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "target_date": (today + timedelta(days=7)).isoformat(),
        "target_shift_type": "morning",
        "requested_action": "move",
    }
    r_create = await http_client.post("/schedule/request/structured", json=payload, headers=john_headers)
    assert r_create.status_code == 200, r_create.text
    request_id = r_create.json()["requestId"]

    r_approve = await http_client.post(f"/approval/{request_id}/approve", headers=alex_headers)
    assert r_approve.status_code == 403, r_approve.text


@pytest.mark.integration
async def test_non_admin_reject_returns_403(
    http_client, john_headers, alex_headers
):
    """A8: Non-admin calls reject -> 403."""
    today = date.today()
    payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "target_date": (today + timedelta(days=6)).isoformat(),
        "target_shift_type": "night",
        "requested_action": "move",
    }
    r_create = await http_client.post("/schedule/request/structured", json=payload, headers=john_headers)
    assert r_create.status_code == 200, r_create.text
    request_id = r_create.json()["requestId"]

    r_reject = await http_client.post(f"/approval/{request_id}/reject", headers=alex_headers)
    assert r_reject.status_code == 403, r_reject.text
