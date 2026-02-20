from datetime import date
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Employee, Shift, ShiftType
from backend.schemas import ErrorCode, RuleEngineResult, ValidatedExtraction, RequestedActionEnum


class RuleEngine:
    async def validate_request(self, session: AsyncSession, extraction: ValidatedExtraction) -> RuleEngineResult:
        errors: list[ErrorCode] = []
        details: dict = {}
        suggestions: list[dict] = []

        employees = await self.resolve_employee(
            session, extraction.employee_first_name, extraction.employee_last_name
        )
        if len(employees) == 0:
            errors.append(ErrorCode.rule_employee_not_found)
            employee = None
        elif len(employees) > 1:
            errors.append(ErrorCode.rule_employee_ambiguous)
            employee = None
        else:
            employee = employees[0]
            details["employee_id"] = str(employee.id)

        if extraction.requested_action == RequestedActionEnum.swap:
            partner, partner_errors = await self._resolve_partner_and_validate_swap(
                session, extraction, employee, details
            )
            errors.extend(partner_errors)
            if partner and employee:
                # Side A: partner takes requester's shift (current_shift_*)
                if extraction.current_shift_date and extraction.current_shift_type:
                    skill_ok_a = await self._validate_skill_for_shift(
                        session,
                        extraction.current_shift_date,
                        ShiftType(extraction.current_shift_type.value),
                        partner.skills,
                    )
                    if not skill_ok_a:
                        errors.append(ErrorCode.rule_skill_mismatch)
                    cert_ok_a = self.validate_certifications(partner.certifications)
                    if not cert_ok_a:
                        errors.append(ErrorCode.rule_cert_expired)
                    conflict_a = await self.check_shift_conflict(
                        session,
                        extraction.current_shift_date,
                        ShiftType(extraction.current_shift_type.value),
                        allowed_assignee_id=employee.id,
                    )
                    if conflict_a:
                        errors.append(ErrorCode.rule_conflict)

                # Side B: requester takes partner's shift (target_*)
                skill_ok_b = await self.validate_skill_match(session, extraction, employee.skills)
                if not skill_ok_b:
                    errors.append(ErrorCode.rule_skill_mismatch)
                cert_ok_b = self.validate_certifications(employee.certifications)
                if not cert_ok_b:
                    errors.append(ErrorCode.rule_cert_expired)
                target_shift_type = ShiftType(extraction.target_shift_type.value)
                conflict_b = await self.check_shift_conflict(
                    session,
                    extraction.target_date,
                    target_shift_type,
                    allowed_assignee_id=partner.id,
                )
                if conflict_b:
                    errors.append(ErrorCode.rule_conflict)
                    suggestions = await self.suggest_alternative_employee(
                        session, extraction.target_date, target_shift_type
                    )
        else:
            if employee:
                skill_ok = await self.validate_skill_match(session, extraction, employee.skills)
                if not skill_ok:
                    errors.append(ErrorCode.rule_skill_mismatch)
                cert_ok = self.validate_certifications(employee.certifications)
                if not cert_ok:
                    errors.append(ErrorCode.rule_cert_expired)
            target_shift_type = ShiftType(extraction.target_shift_type.value)
            conflict = False
            if employee:
                # For cover: conflict only if the shift is taken by someone other than the requester.
                # Explicitly check requester's shift first so we don't falsely conflict when they own it.
                if extraction.requested_action == RequestedActionEnum.cover:
                    requester_shift = await session.scalar(
                        select(Shift).where(
                            and_(
                                Shift.date == extraction.target_date,
                                Shift.type == target_shift_type,
                                Shift.assigned_employee_id == employee.id,
                            )
                        )
                    )
                    if requester_shift is None:
                        conflict = await self.check_shift_conflict(
                            session, extraction.target_date, target_shift_type, allowed_assignee_id=None
                        )
                else:
                    conflict = await self.check_shift_conflict(
                        session, extraction.target_date, target_shift_type, allowed_assignee_id=employee.id
                    )
            if conflict:
                errors.append(ErrorCode.rule_conflict)
                suggestions = await self.suggest_alternative_employee(
                    session, extraction.target_date, target_shift_type
                )

        return RuleEngineResult(
            valid=not errors,
            errorCodes=errors,
            reason="Validation passed." if not errors else "Deterministic validation failed.",
            suggestions=suggestions,
            validationDetails=details,
        )

    async def _resolve_partner_and_validate_swap(
        self,
        session: AsyncSession,
        extraction: ValidatedExtraction,
        requester: Employee | None,
        details: dict,
    ) -> tuple[Employee | None, list[ErrorCode]]:
        errs: list[ErrorCode] = []
        partner_first = extraction.partner_employee_first_name or ""
        partner_last = extraction.partner_employee_last_name or ""
        if not partner_first.strip() and not partner_last.strip():
            errs.append(ErrorCode.rule_employee_not_found)
            return None, errs
        partners = await self.resolve_employee(session, partner_first or None, partner_last or None)
        if len(partners) == 0:
            errs.append(ErrorCode.rule_employee_not_found)
            return None, errs
        if len(partners) > 1:
            errs.append(ErrorCode.rule_employee_ambiguous)
            return None, errs
        details["partner_employee_id"] = str(partners[0].id)
        return partners[0], errs

    async def resolve_employee(
        self,
        session: AsyncSession,
        first_name: str | None,
        last_name: str | None,
    ) -> list[Employee]:
        """Resolve by first only, last only, or both. Case-insensitive. Returns 0, 1, or many."""
        first = (first_name or "").strip() or None
        last = (last_name or "").strip() or None
        if not first and not last:
            return []
        # Case-insensitive match so "john"/"doe" finds "John"/"Doe"
        if first and last:
            stmt = select(Employee).where(
                Employee.first_name.ilike(first),
                Employee.last_name.ilike(last),
            )
        elif first:
            stmt = select(Employee).where(Employee.first_name.ilike(first))
        else:
            stmt = select(Employee).where(Employee.last_name.ilike(last))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def validate_employee_exists(self, session: AsyncSession, employee_first_name: str, employee_last_name: str | None = None) -> Employee | None:
        """Convenience: returns single employee or None. Use resolve_employee for ambiguous handling."""
        employees = await self.resolve_employee(session, employee_first_name, employee_last_name)
        return employees[0] if len(employees) == 1 else None

    async def validate_skill_match(
        self,
        session: AsyncSession,
        extraction: ValidatedExtraction,
        employee_skills: dict,
    ) -> bool:
        target_shift = ShiftType(extraction.target_shift_type.value)
        shift = await session.scalar(
            select(Shift).where(
                and_(
                    Shift.date == extraction.target_date,
                    Shift.type == target_shift,
                )
            )
        )
        if not shift:
            return True
        required = set((shift.required_skills or {}).get("skills", []))
        employee_set = set((employee_skills or {}).get("skills", []))
        return required.issubset(employee_set)

    def validate_certifications(self, certifications: dict) -> bool:
        if not certifications:
            return True
        expired = certifications.get("expired", False)
        return not expired

    async def _validate_skill_for_shift(
        self,
        session: AsyncSession,
        shift_date: date,
        shift_type: ShiftType,
        employee_skills: dict,
    ) -> bool:
        shift = await session.scalar(
            select(Shift).where(
                and_(Shift.date == shift_date, Shift.type == shift_type)
            )
        )
        if not shift:
            return True
        required = set((shift.required_skills or {}).get("skills", []))
        employee_set = set((employee_skills or {}).get("skills", []))
        return required.issubset(employee_set)

    async def check_shift_conflict(
        self,
        session: AsyncSession,
        shift_date: date,
        shift_type: ShiftType,
        allowed_assignee_id: UUID | None = None,
    ) -> bool:
        """True if shift is taken by someone other than allowed_assignee_id."""
        existing = await session.scalar(
            select(Shift).where(
                and_(
                    Shift.date == shift_date,
                    Shift.type == shift_type,
                    Shift.assigned_employee_id.is_not(None),
                )
            )
        )
        if existing is None:
            return False
        if allowed_assignee_id is not None and existing.assigned_employee_id == allowed_assignee_id:
            return False
        return True

    async def suggest_alternative_employee(
        self, session: AsyncSession, shift_date: date, shift_type: ShiftType
    ) -> list[dict]:
        shifts = await session.execute(
            select(Shift, Employee)
            .join(Employee, Shift.assigned_employee_id == Employee.id, isouter=True)
            .where(and_(Shift.date == shift_date, Shift.type == shift_type))
        )
        taken_ids = {row.Employee.id for row in shifts if row.Employee is not None}
        result = await session.execute(select(Employee))
        candidates = result.scalars().all()
        suggestions = []
        for employee in candidates:
            if employee.id in taken_ids:
                continue
            suggestions.append({"employee_first_name": employee.first_name, "employee_last_name": employee.last_name, "reason": "Available for requested slot"})
            if len(suggestions) >= 3:
                break
        return suggestions

    async def get_eligible_candidates_for_shift(
        self, session: AsyncSession, shift: Shift
    ) -> list[tuple[Employee, str]]:
        """Return (Employee, reason) for employees who can take this shift (skills, certs, no conflict)."""
        result = await session.execute(select(Employee))
        all_employees = result.scalars().all()
        out: list[tuple[Employee, str]] = []
        for emp in all_employees:
            reasons: list[str] = []
            skill_ok = await self._validate_skill_for_shift(
                session, shift.date, shift.type, emp.skills or {}
            )
            if not skill_ok:
                reasons.append("skill mismatch")
            cert_ok = self.validate_certifications(emp.certifications or {})
            if not cert_ok:
                reasons.append("cert expired")
            conflict = await self.check_shift_conflict(
                session, shift.date, shift.type, allowed_assignee_id=emp.id
            )
            if not conflict:
                reasons.append("already has shift that day/type")
            if reasons:
                continue
            out.append((emp, "Eligible"))
        return out

