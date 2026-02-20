"""
Seed the database with employees and shifts for demos and edge-case testing.

Run from project root with:
  python -m backend.scripts.seed_db

Uses DATABASE_URL from environment (or .env). Idempotent: re-run to reset
to seed state (drops and recreates seed data by name).
"""

import asyncio
import os
import uuid
from datetime import date, timedelta

# Ensure we load env before config
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import SessionLocal, init_db
from backend.models import Employee, EmployeeRole, Shift, ShiftType


# --- Seed data: normal + edge cases ---
# One account is admin for dev/testing: Priya Smith (role=admin). Others are employee.

def get_employees():
    return [
        {
            "first_name": "John",
            "last_name": "Doe",
            "role": EmployeeRole.employee,
            "certifications": {"expired": False},
            "skills": {"skills": ["basic", "safety"]},
            "availability": {},
        },
        {
            "first_name": "Priya",
            "last_name": "Smith",
            "role": EmployeeRole.admin,
            "certifications": {"expired": False},
            "skills": {"skills": ["basic", "safety", "advanced"]},
            "availability": {},
        },
        {
            "first_name": "Alex",
            "last_name": "Johnson",
            "role": EmployeeRole.employee,
            "certifications": {"expired": False},
            "skills": {"skills": ["basic"]},
            "availability": {},
        },
        {
            "first_name": "Michael",
            "last_name": "Johnson",
            "role": EmployeeRole.employee,
            "certifications": {"expired": False},
            "skills": {"skills": ["safety"]},
            "availability": {},
        },
        # Edge: rule engine will reject (RULE_CERT_EXPIRED)
        {
            "first_name": "ExpiredCert",
            "last_name": "Doe",
            "role": EmployeeRole.employee,
            "certifications": {"expired": True},
            "skills": {"skills": ["basic"]},
            "availability": {},
        },
        # Edge: no advanced skill -> RULE_SKILL_MISMATCH if assigned to shift requiring advanced
        {
            "first_name": "NoAdvanced",
            "last_name": "Smith",
            "role": EmployeeRole.employee,
            "certifications": {"expired": False},
            "skills": {"skills": ["basic"]},
            "availability": {},
        },
    ]


def get_shifts(employee_by_name: dict[str, uuid.UUID]):
    """Shifts to seed; some assigned, some open. Uses employee ids from current DB."""
    today = date.today()
    john_id = employee_by_name.get("John Doe")
    priya_id = employee_by_name.get("Priya Smith")
    alex_id = employee_by_name.get("Alex Johnson")
    michael_id = employee_by_name.get("Michael Johnson")
    return [
        # Assigned shifts (for conflict / swap tests)
        {"date": today + timedelta(days=1), "type": ShiftType.night, "required_skills": {"skills": ["basic"]}, "assigned_employee_id": john_id},
        {"date": today + timedelta(days=2), "type": ShiftType.morning, "required_skills": {"skills": ["basic"]}, "assigned_employee_id": priya_id},
        {"date": today + timedelta(days=3), "type": ShiftType.night, "required_skills": {"skills": ["basic", "advanced"]}, "assigned_employee_id": priya_id},
        # Open shift requiring advanced -> assign NoAdvanced will trigger RULE_SKILL_MISMATCH
        {"date": today + timedelta(days=4), "type": ShiftType.morning, "required_skills": {"skills": ["advanced"]}, "assigned_employee_id": None},
        {"date": today + timedelta(days=5), "type": ShiftType.night, "required_skills": {"skills": ["basic"]}, "assigned_employee_id": alex_id},
        {"date": today + timedelta(days=6), "type": ShiftType.morning, "required_skills": {"skills": ["safety"]}, "assigned_employee_id": michael_id},
    ]


async def seed(session: AsyncSession) -> None:
    # Ensure tables exist
    await init_db()

    # Upsert employees by name (idempotent)
    existing = await session.execute(select(Employee))
    existing_by_name = {e.full_name: e for e in existing.scalars().all()}
    employee_by_name: dict[str, uuid.UUID] = {}

    for data in get_employees():
        name = data["first_name"] + " " + data["last_name"]
        if name in existing_by_name:
            emp = existing_by_name[name]
            emp.role = data["role"]
            emp.certifications = data["certifications"]
            emp.skills = data["skills"]
            emp.availability = data["availability"]
            employee_by_name[name] = emp.id
        else:
            emp = Employee(
                first_name=data["first_name"],
                last_name=data["last_name"],
                role=data["role"],
                certifications=data["certifications"],
                skills=data["skills"],
                availability=data["availability"],
            )
            session.add(emp)
            await session.flush()
            employee_by_name[name] = emp.id

    await session.commit()
    # New session for shifts so we have committed employee ids
    async with SessionLocal() as session2:
        today = date.today()
        await session2.execute(
            delete(Shift).where(and_(Shift.date >= today, Shift.date <= today + timedelta(days=10)))
        )
        await session2.commit()

    async with SessionLocal() as session3:
        for row in get_shifts(employee_by_name):
            session3.add(Shift(**row))
        await session3.commit()

    print("Seed complete: employees and shifts created/updated.")


if __name__ == "__main__":
    async def _run():
        async with SessionLocal() as session:
            await seed(session)

    asyncio.run(_run())
