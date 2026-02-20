"""Integration tests: employees CRUD (list, create, update, delete, duplicate name, admin-only).
Stories CRUD1–CRUD6.
"""
import pytest


@pytest.mark.integration
async def test_list_employees_ordered_by_name(
    http_client, admin_headers
):
    """CRUD1: Admin lists employees -> GET /employees list ordered by last_name, first_name; includes role."""
    r = await http_client.get("/employees")
    assert r.status_code == 200, r.text
    employees = r.json()
    assert isinstance(employees, list)
    for e in employees:
        assert "id" in e
        assert "full_name" in e
        assert "first_name" in e
        assert "last_name" in e
        assert "role" in e
    # Check ordering: by last_name, first_name
    names = [(e["last_name"], e["first_name"]) for e in employees]
    assert names == sorted(names)


@pytest.mark.integration
async def test_admin_create_employee_returns_201(
    http_client, admin_headers
):
    """CRUD2: Admin creates employee -> POST /employees -> 201 with EmployeeOut."""
    payload = {
        "first_name": "Test",
        "last_name": "User",
        "role": "employee",
        "certifications": {},
        "skills": {"skills": ["basic"]},
        "availability": {},
    }
    r = await http_client.post("/employees", json=payload, headers=admin_headers)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"
    assert data["role"] == "employee"
    assert "id" in data


@pytest.mark.integration
async def test_admin_update_employee_returns_200(
    http_client, admin_headers, employee_ids
):
    """CRUD3: Admin updates employee (e.g. role) -> PATCH /employees/{id} -> 200 with updated employee."""
    # Use an existing employee (e.g. Michael Johnson)
    eid = employee_ids.get("Michael Johnson")
    assert eid, "Michael Johnson not in seed"
    payload = {"role": "employee"}
    r = await http_client.patch(f"/employees/{eid}", json=payload, headers=admin_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["id"] == eid


@pytest.mark.integration
async def test_admin_delete_employee_returns_204(
    http_client, admin_headers
):
    """CRUD4: Admin deletes employee -> DELETE /employees/{id} -> 204."""
    # Create then delete to avoid breaking seed
    payload = {
        "first_name": "ToDelete",
        "last_name": "User",
        "role": "employee",
        "certifications": {},
        "skills": {},
        "availability": {},
    }
    r_create = await http_client.post("/employees", json=payload, headers=admin_headers)
    assert r_create.status_code == 201, r_create.text
    eid = r_create.json()["id"]

    r_del = await http_client.delete(f"/employees/{eid}", headers=admin_headers)
    assert r_del.status_code == 204, r_del.text


@pytest.mark.integration
async def test_patch_employee_duplicate_name_returns_409(
    http_client, admin_headers, employee_ids
):
    """CRUD5: PATCH employee to duplicate another's name -> 409 EMPLOYEE_DUPLICATE_NAME."""
    # Alex Johnson -> change to John Doe (already exists)
    alex_id = employee_ids.get("Alex Johnson")
    assert alex_id
    payload = {"first_name": "John", "last_name": "Doe"}
    r = await http_client.patch(f"/employees/{alex_id}", json=payload, headers=admin_headers)
    assert r.status_code == 409, r.text
    assert r.json().get("errorCode") == "EMPLOYEE_DUPLICATE_NAME"


@pytest.mark.integration
async def test_non_admin_post_employees_returns_403(
    http_client, john_headers
):
    """CRUD6: Non-admin POST /employees -> 403."""
    payload = {
        "first_name": "New",
        "last_name": "User",
        "role": "employee",
        "certifications": {},
        "skills": {},
        "availability": {},
    }
    r = await http_client.post("/employees", json=payload, headers=john_headers)
    assert r.status_code == 403, r.text


@pytest.mark.integration
async def test_non_admin_patch_employees_returns_403(
    http_client, john_headers, employee_ids
):
    """CRUD6: Non-admin PATCH /employees/{id} -> 403."""
    eid = employee_ids.get("Alex Johnson")
    assert eid
    r = await http_client.patch(f"/employees/{eid}", json={"role": "admin"}, headers=john_headers)
    assert r.status_code == 403, r.text


@pytest.mark.integration
async def test_non_admin_delete_employees_returns_403(
    http_client, john_headers, employee_ids
):
    """CRUD6: Non-admin DELETE /employees/{id} -> 403."""
    eid = employee_ids.get("Alex Johnson")
    assert eid
    r = await http_client.delete(f"/employees/{eid}", headers=john_headers)
    assert r.status_code == 403, r.text
