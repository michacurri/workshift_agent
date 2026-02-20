"""Integration tests: partner consent flow (list pending, accept, reject, 409/403 on invalid state or wrong user).
Stories P1–P5.
"""
from datetime import date, timedelta

import pytest


@pytest.mark.integration
async def test_partner_sees_pending_consents_with_summary_and_workload(
    http_client, john_headers, alex_headers, employee_ids
):
    """P1: Partner opens Consents -> GET /partner/pending returns items for partner_employee_id=current user, status=pending_partner; summary and workload."""
    today = date.today()
    swap_payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "current_shift_date": (today + timedelta(days=8)).isoformat(),
        "current_shift_type": "morning",
        "target_date": (today + timedelta(days=5)).isoformat(),
        "target_shift_type": "night",
        "requested_action": "swap",
        "partner_employee_first_name": "Alex",
        "partner_employee_last_name": "Johnson",
        "partner_shift_date": (today + timedelta(days=5)).isoformat(),
        "partner_shift_type": "night",
    }
    r_create = await http_client.post("/schedule/request/structured", json=swap_payload, headers=john_headers)
    assert r_create.status_code == 200, r_create.text

    r_pending = await http_client.get("/partner/pending", headers=alex_headers)
    assert r_pending.status_code == 200, r_pending.text
    items = r_pending.json()
    assert isinstance(items, list)
    # Alex should see the swap request from John
    assert len(items) >= 1
    one = next((x for x in items if x.get("requestId") == r_create.json()["requestId"]), None)
    assert one is not None
    assert "summary" in one
    assert "workload_shifts_this_week" in one


@pytest.mark.integration
async def test_partner_accept_sets_status_pending_admin(
    http_client, john_headers, alex_headers, admin_headers
):
    """P2: Partner accepts -> POST /partner/{id}/accept -> status pending_admin; request in approval queue."""
    today = date.today()
    swap_payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "current_shift_date": (today + timedelta(days=8)).isoformat(),
        "current_shift_type": "morning",
        "target_date": (today + timedelta(days=5)).isoformat(),
        "target_shift_type": "night",
        "requested_action": "swap",
        "partner_employee_first_name": "Alex",
        "partner_employee_last_name": "Johnson",
        "partner_shift_date": (today + timedelta(days=5)).isoformat(),
        "partner_shift_type": "night",
    }
    r_create = await http_client.post("/schedule/request/structured", json=swap_payload, headers=john_headers)
    assert r_create.status_code == 200, r_create.text
    request_id = r_create.json()["requestId"]

    r_accept = await http_client.post(f"/partner/{request_id}/accept", headers=alex_headers)
    assert r_accept.status_code == 200, r_accept.text
    assert r_accept.json().get("status") == "pending_admin"

    # Admin should see it in approval pending
    r_approval = await http_client.get("/approval/pending", headers=admin_headers)
    assert r_approval.status_code == 200, r_approval.text
    pending = r_approval.json()
    ids = [p["requestId"] for p in pending]
    assert request_id in ids


@pytest.mark.integration
async def test_partner_reject_sets_status_partner_rejected(
    http_client, john_headers, alex_headers, admin_headers
):
    """P3: Partner rejects -> POST /partner/{id}/reject -> status partner_rejected; not in approval list."""
    today = date.today()
    swap_payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "target_date": (today + timedelta(days=5)).isoformat(),
        "target_shift_type": "night",
        "requested_action": "swap",
        "partner_employee_first_name": "Alex",
        "partner_employee_last_name": "Johnson",
        "partner_shift_date": (today + timedelta(days=5)).isoformat(),
        "partner_shift_type": "night",
    }
    r_create = await http_client.post("/schedule/request/structured", json=swap_payload, headers=john_headers)
    assert r_create.status_code == 200, r_create.text
    request_id = r_create.json()["requestId"]

    r_reject = await http_client.post(f"/partner/{request_id}/reject", headers=alex_headers)
    assert r_reject.status_code == 200, r_reject.text
    assert r_reject.json().get("status") == "partner_rejected"

    # Should not appear in admin approval pending
    r_approval = await http_client.get("/approval/pending", headers=admin_headers)
    assert r_approval.status_code == 200, r_approval.text
    pending = r_approval.json()
    ids = [p["requestId"] for p in pending]
    assert request_id not in ids


@pytest.mark.integration
async def test_partner_accept_non_pending_partner_returns_409(
    http_client, john_headers, alex_headers
):
    """P4: Partner tries to accept a request that is not pending_partner (e.g. already accepted) -> 409; status unchanged."""
    today = date.today()
    swap_payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "target_date": (today + timedelta(days=5)).isoformat(),
        "target_shift_type": "night",
        "requested_action": "swap",
        "partner_employee_first_name": "Alex",
        "partner_employee_last_name": "Johnson",
        "partner_shift_date": (today + timedelta(days=5)).isoformat(),
        "partner_shift_type": "night",
    }
    r_create = await http_client.post("/schedule/request/structured", json=swap_payload, headers=john_headers)
    assert r_create.status_code == 200, r_create.text
    request_id = r_create.json()["requestId"]

    await http_client.post(f"/partner/{request_id}/accept", headers=alex_headers)
    # Second accept should fail
    r_accept2 = await http_client.post(f"/partner/{request_id}/accept", headers=alex_headers)
    assert r_accept2.status_code in (403, 409), r_accept2.text


@pytest.mark.integration
async def test_non_partner_cannot_accept_returns_403_or_409(
    http_client, john_headers, alex_headers, admin_headers
):
    """P5: Non-partner (e.g. admin) tries to accept a request where they are not the partner -> 403/409."""
    today = date.today()
    swap_payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "target_date": (today + timedelta(days=5)).isoformat(),
        "target_shift_type": "night",
        "requested_action": "swap",
        "partner_employee_first_name": "Alex",
        "partner_employee_last_name": "Johnson",
        "partner_shift_date": (today + timedelta(days=5)).isoformat(),
        "partner_shift_type": "night",
    }
    r_create = await http_client.post("/schedule/request/structured", json=swap_payload, headers=john_headers)
    assert r_create.status_code == 200, r_create.text
    request_id = r_create.json()["requestId"]

    # Admin is not the partner; trying to accept as admin should fail
    r_accept = await http_client.post(f"/partner/{request_id}/accept", headers=admin_headers)
    assert r_accept.status_code in (403, 409), r_accept.text
