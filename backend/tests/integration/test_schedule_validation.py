"""Integration tests: schedule validation rules (employee not found, conflict, skill mismatch, cert expired).
Stories E8–E11.
"""
from datetime import date, timedelta

import pytest


@pytest.mark.integration
async def test_employee_not_found_returns_rule_error(
    http_client, admin_headers
):
    """E8: Employee not in DB -> validation fails with RULE_EMPLOYEE_NOT_FOUND; no request created."""
    today = date.today()
    payload = {
        "employee_first_name": "Nobody",
        "employee_last_name": "Nowhere",
        "target_date": (today + timedelta(days=3)).isoformat(),
        "target_shift_type": "morning",
        "requested_action": "move",
    }
    r = await http_client.post("/schedule/request/structured", json=payload, headers=admin_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") == "rejected"
    assert "RULE_EMPLOYEE_NOT_FOUND" in data.get("validation", {}).get("errorCodes", [])


@pytest.mark.integration
async def test_shift_conflict_returns_rule_error(
    http_client, john_headers
):
    """E9: Shift conflict (target already assigned to someone else) -> RULE_CONFLICT, suggestions."""
    today = date.today()
    # Seed: day2 morning is assigned to Priya. Request move for John to day2 morning -> conflict.
    payload = {
        "employee_first_name": "John",
        "employee_last_name": "Doe",
        "target_date": (today + timedelta(days=2)).isoformat(),
        "target_shift_type": "morning",
        "requested_action": "move",
    }
    r = await http_client.post("/schedule/request/structured", json=payload, headers=john_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") == "rejected"
    assert "RULE_CONFLICT" in data.get("validation", {}).get("errorCodes", [])


@pytest.mark.integration
async def test_skill_mismatch_returns_rule_error(
    http_client, employee_ids
):
    """E10: NoAdvanced has no 'advanced' skill; shift requires advanced -> RULE_SKILL_MISMATCH."""
    today = date.today()
    # Seed: day4 morning requires advanced; NoAdvanced Smith has only basic.
    no_advanced_id = employee_ids.get("NoAdvanced Smith")
    assert no_advanced_id, "Seed employee NoAdvanced Smith not found"
    headers = {"X-Employee-Id": no_advanced_id, "Content-Type": "application/json"}
    payload = {
        "employee_first_name": "NoAdvanced",
        "employee_last_name": "Smith",
        "target_date": (today + timedelta(days=4)).isoformat(),
        "target_shift_type": "morning",
        "requested_action": "move",
    }
    r = await http_client.post("/schedule/request/structured", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") == "rejected"
    assert "RULE_SKILL_MISMATCH" in data.get("validation", {}).get("errorCodes", [])


@pytest.mark.integration
async def test_cert_expired_returns_rule_error(
    http_client, employee_ids
):
    """E11: ExpiredCert Doe has expired cert -> RULE_CERT_EXPIRED."""
    today = date.today()
    expired_id = employee_ids.get("ExpiredCert Doe")
    assert expired_id, "Seed employee ExpiredCert Doe not found"
    headers = {"X-Employee-Id": expired_id, "Content-Type": "application/json"}
    payload = {
        "employee_first_name": "ExpiredCert",
        "employee_last_name": "Doe",
        "target_date": (today + timedelta(days=5)).isoformat(),
        "target_shift_type": "night",
        "requested_action": "move",
    }
    r = await http_client.post("/schedule/request/structured", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") == "rejected"
    assert "RULE_CERT_EXPIRED" in data.get("validation", {}).get("errorCodes", [])
