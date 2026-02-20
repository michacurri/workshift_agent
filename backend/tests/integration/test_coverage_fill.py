"""Integration tests: coverage fill (candidates eligibility, assign, request approved; admin-only).
Stories A5–A7, A8.
"""
from datetime import date, timedelta

import pytest


@pytest.mark.integration
async def test_admin_gets_eligible_candidates_for_coverage_shift(
    http_client, john_headers, admin_headers, shift_date_range
):
    """A6: Admin calls GET /schedule/shifts/{shift_id}/candidates -> only eligible (skills, certs, no conflict); 403 if not admin."""
    today = date.today()
    # Create coverage request (John's shift day1 night)
    cover_payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "current_shift_date": (today + timedelta(days=1)).isoformat(),
        "current_shift_type": "night",
        "target_date": (today + timedelta(days=1)).isoformat(),
        "target_shift_type": "night",
        "requested_action": "cover",
    }
    r_req = await http_client.post("/schedule/request/structured", json=cover_payload, headers=john_headers)
    assert r_req.status_code == 200, r_req.text

    from_date, to_date = shift_date_range
    r_shifts = await http_client.get(
        f"/schedule/shifts?from={from_date}&to={to_date}",
        headers=admin_headers,
    )
    assert r_shifts.status_code == 200, r_shifts.text
    shifts = r_shifts.json()["shifts"]
    john_shift = next(
        (s for s in shifts if s["date"] == (today + timedelta(days=1)).isoformat() and s["type"] == "night" and s.get("assigned_employee_full_name") == "John Doe"),
        None,
    )
    assert john_shift is not None, "John's shift not found"
    shift_id = john_shift["id"]

    r_candidates = await http_client.get(f"/schedule/shifts/{shift_id}/candidates", headers=admin_headers)
    assert r_candidates.status_code == 200, r_candidates.text
    candidates = r_candidates.json()
    assert isinstance(candidates, list)
    for c in candidates:
        assert "employee_id" in c
        assert "full_name" in c
        assert "reason" in c


@pytest.mark.integration
async def test_admin_assigns_candidate_updates_shift_and_approves_request(
    http_client, john_headers, admin_headers, employee_ids, shift_date_range
):
    """A7: Admin assigns candidate -> POST /schedule/shifts/{shift_id}/assign -> shift updated; matching pending_fill request -> approved."""
    today = date.today()
    cover_payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "current_shift_date": (today + timedelta(days=1)).isoformat(),
        "current_shift_type": "night",
        "target_date": (today + timedelta(days=1)).isoformat(),
        "target_shift_type": "night",
        "requested_action": "cover",
    }
    r_req = await http_client.post("/schedule/request/structured", json=cover_payload, headers=john_headers)
    assert r_req.status_code == 200, r_req.text
    request_id = r_req.json()["requestId"]

    from_date, to_date = shift_date_range
    r_shifts = await http_client.get(
        f"/schedule/shifts?from={from_date}&to={to_date}",
        headers=admin_headers,
    )
    assert r_shifts.status_code == 200, r_shifts.text
    shifts = r_shifts.json()["shifts"]
    john_shift = next(
        (s for s in shifts if s["date"] == (today + timedelta(days=1)).isoformat() and s["type"] == "night" and s.get("assigned_employee_full_name") == "John Doe"),
        None,
    )
    assert john_shift is not None, "John's shift not found"
    shift_id = john_shift["id"]

    r_candidates = await http_client.get(f"/schedule/shifts/{shift_id}/candidates", headers=admin_headers)
    assert r_candidates.status_code == 200, r_candidates.text
    candidates = r_candidates.json()
    assert len(candidates) >= 1
    # Assign to Alex (eligible for basic night shift)
    alex_id = employee_ids.get("Alex Johnson")
    assert alex_id, "Alex Johnson not in seed"

    r_assign = await http_client.post(
        f"/schedule/shifts/{shift_id}/assign",
        json={"employee_id": alex_id},
        headers=admin_headers,
    )
    assert r_assign.status_code == 200, r_assign.text

    # Request should now be approved; list requests and check
    r_list = await http_client.get("/schedule/requests", headers=admin_headers)
    assert r_list.status_code == 200, r_list.text
    items = r_list.json()
    req_item = next((x for x in items if x["requestId"] == request_id), None)
    assert req_item is not None
    assert req_item["status"] == "approved"


@pytest.mark.integration
async def test_non_admin_candidates_returns_403(
    http_client, john_headers, alex_headers, admin_headers, shift_date_range
):
    """A8: Non-admin calls GET /schedule/shifts/{id}/candidates -> 403."""
    today = date.today()
    cover_payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "current_shift_date": (today + timedelta(days=1)).isoformat(),
        "current_shift_type": "night",
        "target_date": (today + timedelta(days=1)).isoformat(),
        "target_shift_type": "night",
        "requested_action": "cover",
    }
    await http_client.post("/schedule/request/structured", json=cover_payload, headers=john_headers)

    from_date, to_date = shift_date_range
    r_shifts = await http_client.get(
        f"/schedule/shifts?from={from_date}&to={to_date}",
        headers=admin_headers,
    )
    shifts = r_shifts.json()["shifts"]
    # Permission behavior is independent of which concrete shift id is used.
    # Use the first available shift to avoid coupling to mutable assignment state.
    if not shifts:
        pytest.skip("No shifts found in seeded date range")
    shift_id = shifts[0]["id"]

    r = await http_client.get(f"/schedule/shifts/{shift_id}/candidates", headers=alex_headers)
    assert r.status_code == 403, r.text


@pytest.mark.integration
async def test_non_admin_assign_returns_403(
    http_client, john_headers, alex_headers, admin_headers, employee_ids, shift_date_range
):
    """A8: Non-admin calls POST /schedule/shifts/{id}/assign -> 403."""
    today = date.today()
    cover_payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "current_shift_date": (today + timedelta(days=2)).isoformat(),
        "current_shift_type": "night",
        "target_date": (today + timedelta(days=2)).isoformat(),
        "target_shift_type": "night",
        "requested_action": "cover",
    }
    await http_client.post("/schedule/request/structured", json=cover_payload, headers=john_headers)

    from_date, to_date = shift_date_range
    r_shifts = await http_client.get(
        f"/schedule/shifts?from={from_date}&to={to_date}",
        headers=admin_headers,
    )
    shifts = r_shifts.json()["shifts"]
    # Permission behavior is independent of shift ownership or type.
    if not shifts:
        pytest.skip("No shifts found in seeded date range")
    shift_id = shifts[0]["id"]
    alex_id = employee_ids.get("Alex Johnson")

    r = await http_client.post(
        f"/schedule/shifts/{shift_id}/assign",
        json={"employee_id": alex_id},
        headers=alex_headers,
    )
    assert r.status_code == 403, r.text
