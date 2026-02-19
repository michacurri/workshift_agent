from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db_session
from backend.deps import require_admin
from backend.errors import AppError
from backend.models import Employee, EmployeeRole
from backend.schemas import EmployeeCreate, EmployeeOut, EmployeeUpdate, ErrorCode

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeOut])
async def list_employees(session: AsyncSession = Depends(get_db_session)) -> list[EmployeeOut]:
    result = await session.execute(select(Employee).order_by(Employee.last_name, Employee.first_name))
    employees = result.scalars().all()
    return [EmployeeOut.model_validate(e) for e in employees]


@router.get("/{employee_id}", response_model=EmployeeOut)
async def get_employee(
    employee_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> EmployeeOut:
    employee = await session.get(Employee, employee_id)
    if not employee:
        raise AppError(
            ErrorCode.employee_not_found,
            "Employee not found.",
            f"No employee with id {employee_id}",
            404,
        )
    return EmployeeOut.model_validate(employee)


@router.post("", response_model=EmployeeOut, status_code=201)
async def create_employee(
    payload: EmployeeCreate,
    session: AsyncSession = Depends(get_db_session),
    _: Employee = Depends(require_admin),
) -> EmployeeOut:
    employee = Employee(
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=EmployeeRole(payload.role.value),
        certifications=payload.certifications,
        skills=payload.skills,
        availability=payload.availability,
    )
    session.add(employee)
    await session.commit()
    await session.refresh(employee)
    return EmployeeOut.model_validate(employee)


@router.patch("/{employee_id}", response_model=EmployeeOut)
async def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdate,
    session: AsyncSession = Depends(get_db_session),
    _: Employee = Depends(require_admin),
) -> EmployeeOut:
    employee = await session.get(Employee, employee_id)
    if not employee:
        raise AppError(
            ErrorCode.employee_not_found,
            "Employee not found.",
            f"No employee with id {employee_id}",
            404,
        )
    if payload.first_name is not None:
        employee.first_name = payload.first_name
    if payload.last_name is not None:
        employee.last_name = payload.last_name
    if payload.first_name is not None or payload.last_name is not None:
        other = await session.scalar(select(Employee).where(Employee.first_name == employee.first_name, Employee.last_name == employee.last_name, Employee.id != employee_id))
        if other:
            raise AppError(
                ErrorCode.employee_duplicate_name,
                "Another employee already has this name.",
                f"Duplicate name: {employee.first_name} {employee.last_name}",
                409,
            )
    if payload.role is not None:
        employee.role = EmployeeRole(payload.role.value)
    if payload.certifications is not None:
        employee.certifications = payload.certifications
    if payload.skills is not None:
        employee.skills = payload.skills
    if payload.availability is not None:
        employee.availability = payload.availability
    await session.commit()
    await session.refresh(employee)
    return EmployeeOut.model_validate(employee)


@router.delete("/{employee_id}", status_code=204)
async def delete_employee(
    employee_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _: Employee = Depends(require_admin),
) -> None:
    employee = await session.get(Employee, employee_id)
    if not employee:
        raise AppError(
            ErrorCode.employee_not_found,
            "Employee not found.",
            f"No employee with id {employee_id}",
            404,
        )
    await session.delete(employee)
    await session.commit()
