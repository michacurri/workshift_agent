from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db_session
from backend.errors import AppError
from backend.models import Employee, EmployeeRole
from backend.schemas import ErrorCode


async def get_current_user(
    session: AsyncSession = Depends(get_db_session),
    x_employee_id: str | None = Header(default=None, alias="X-Employee-Id"),
) -> Employee:
    if not x_employee_id:
        raise AppError(
            ErrorCode.validation_error,
            "Authentication is required for this operation.",
            "Missing X-Employee-Id header.",
            401,
        )
    try:
        employee_id = UUID(x_employee_id)
    except ValueError as exc:  # noqa: B904
        raise AppError(
            ErrorCode.validation_error,
            "Invalid authentication token.",
            f"Invalid X-Employee-Id header: {x_employee_id}",
            401,
        ) from exc

    employee = await session.get(Employee, employee_id)
    if not employee:
        raise AppError(
            ErrorCode.employee_not_found,
            "Employee for this session no longer exists.",
            f"Employee {employee_id} not found for current user.",
            401,
        )
    return employee


async def require_admin(current_user: Employee = Depends(get_current_user)) -> Employee:
    if current_user.role != EmployeeRole.admin:
        raise AppError(
            ErrorCode.validation_error,
            "You do not have permission to perform this action.",
            f"User {current_user.id} is not an admin.",
            403,
        )
    return current_user

