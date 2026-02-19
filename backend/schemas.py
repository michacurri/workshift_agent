from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ShiftTypeEnum(str, Enum):
    morning = "morning"
    night = "night"


class RequestedActionEnum(str, Enum):
    swap = "swap"
    move = "move"
    cover = "cover"


class ErrorCode(str, Enum):
    extraction_unparsable = "EXTRACTION_UNPARSABLE"
    extraction_invalid_schema = "EXTRACTION_INVALID_SCHEMA"
    rule_employee_not_found = "RULE_EMPLOYEE_NOT_FOUND"
    rule_skill_mismatch = "RULE_SKILL_MISMATCH"
    rule_cert_expired = "RULE_CERT_EXPIRED"
    rule_conflict = "RULE_CONFLICT"
    approval_not_pending = "APPROVAL_NOT_PENDING"
    db_error = "DB_ERROR"
    llm_timeout = "LLM_TIMEOUT"
    llm_provider_error = "LLM_PROVIDER_ERROR"
    validation_error = "VALIDATION_ERROR"
    employee_not_found = "EMPLOYEE_NOT_FOUND"
    employee_duplicate_name = "EMPLOYEE_DUPLICATE_NAME"
    rule_employee_ambiguous = "RULE_EMPLOYEE_AMBIGUOUS"


class ParsedExtraction(BaseModel):
    employee_first_name: str
    employee_last_name: str | None = None
    current_shift_date: date | None = None
    current_shift_type: ShiftTypeEnum | None = None
    target_date: date | None = None
    target_shift_type: ShiftTypeEnum | None = None
    requested_action: RequestedActionEnum | None = None
    reason: str | None = None
    partner_employee_first_name: str | None = None
    partner_employee_last_name: str | None = None
    partner_shift_date: date | None = None
    partner_shift_type: ShiftTypeEnum | None = None


class ValidatedExtraction(BaseModel):
    employee_first_name: str
    employee_last_name: str | None = None
    current_shift_date: date | None = None
    current_shift_type: ShiftTypeEnum | None = None
    target_date: date
    target_shift_type: ShiftTypeEnum
    requested_action: RequestedActionEnum = RequestedActionEnum.move
    reason: str | None = None
    partner_employee_first_name: str | None = None
    partner_employee_last_name: str | None = None
    partner_shift_date: date | None = None
    partner_shift_type: ShiftTypeEnum | None = None


class ExtractionResult(BaseModel):
    parsed: ParsedExtraction
    validated: ValidatedExtraction
    raw_payload: dict[str, Any]
    extraction_version: str
    provider_name: str


class ScheduleRequestIn(BaseModel):
    text: str = Field(min_length=3, max_length=5000)


class StructuredRequestIn(BaseModel):
    employee_first_name: str
    employee_last_name: str | None = None
    current_shift_date: date | None = None
    current_shift_type: ShiftTypeEnum | None = None
    target_date: date | None = None
    target_shift_type: ShiftTypeEnum | None = None
    requested_action: RequestedActionEnum | None = None
    reason: str | None = None
    partner_employee_first_name: str | None = None
    partner_employee_last_name: str | None = None
    partner_shift_date: date | None = None
    partner_shift_type: ShiftTypeEnum | None = None


class RuleEngineResult(BaseModel):
    valid: bool
    errorCodes: list[ErrorCode] = Field(default_factory=list)
    reason: str | None = None
    suggestions: list[dict[str, Any]] = Field(default_factory=list)
    validationDetails: dict[str, Any] = Field(default_factory=dict)


class ApiError(BaseModel):
    errorCode: ErrorCode
    userMessage: str
    developerMessage: str
    correlationId: str


class ScheduleRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    requestId: UUID
    status: str
    extractionVersion: str | None = None
    parsed: dict[str, Any] | None = None
    validation: RuleEngineResult
    approvalId: str | None = None
    correlationId: str
    idempotentHit: bool = False
    summary: str | None = None


class PreviewRequestIn(BaseModel):
    """One of text (NL) or structured payload."""
    text: str | None = Field(default=None, min_length=1, max_length=5000)
    structured: StructuredRequestIn | None = None

    @model_validator(mode="after")
    def require_one_of(self) -> "PreviewRequestIn":
        has_text = self.text is not None and len((self.text or "").strip()) > 0
        has_structured = self.structured is not None
        if has_text == has_structured:
            raise ValueError("Provide exactly one of 'text' or 'structured'")
        return self


class PreviewResponse(BaseModel):
    parsed: dict[str, Any]
    validation: RuleEngineResult
    summary: str


class PartnerPendingItem(BaseModel):
    requestId: UUID
    summary: str
    requester_full_name: str | None = None
    requester_shift_date: date | None = None
    requester_shift_type: str | None = None
    partner_shift_date: date | None = None
    partner_shift_type: str | None = None
    submittedAt: datetime
    workload_shifts_this_week: int | None = None

class PendingApprovalItem(BaseModel):
    requestId: UUID
    parsed: dict[str, Any]
    submittedAt: datetime
    requested_action: str | None = None
    requester_full_name: str | None = None
    urgent: bool = False
    requester_shift_date: date | None = None
    requester_shift_type: str | None = None
    partner_full_name: str | None = None
    partner_shift_date: date | None = None
    partner_shift_type: str | None = None
    result_summary: str | None = None


class ApprovalActionOut(BaseModel):
    requestId: UUID
    status: str
    correlationId: str


class MetricsOut(BaseModel):
    total_requests: int
    approval_rate: float
    average_processing_time: float
    parse_time_avg: float
    validation_time_avg: float
    approval_latency_avg: float


class HealthStatus(BaseModel):
    status: str
    latency_ms: float | None = None
    last_error: str | None = None


class ShiftOut(BaseModel):
    id: UUID
    date: date
    type: ShiftTypeEnum
    required_skills: dict[str, Any]
    assigned_employee_id: UUID | None = None
    assigned_employee_full_name: str | None = None


class ShiftsResponse(BaseModel):
    shifts: list[ShiftOut]


class ShiftCandidateOut(BaseModel):
    employee_id: UUID
    full_name: str
    reason: str
    shifts_this_week: int = 0


class ShiftAssignIn(BaseModel):
    employee_id: UUID


class ScheduleRequestListItem(BaseModel):
    requestId: UUID
    status: str
    summary: str | None = None
    created_at: datetime
    requester_full_name: str | None = None
    coverage_shift_id: UUID | None = None
    urgent: bool = False


# --- Employee CRUD ---

class EmployeeRoleEnum(str, Enum):
    employee = "employee"
    admin = "admin"


class EmployeeBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    role: EmployeeRoleEnum = EmployeeRoleEnum.employee
    certifications: dict[str, Any] = Field(default_factory=dict)
    skills: dict[str, Any] = Field(default_factory=dict)
    availability: dict[str, Any] = Field(default_factory=dict)


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=255)
    last_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: EmployeeRoleEnum | None = None
    certifications: dict[str, Any] | None = None
    skills: dict[str, Any] | None = None
    availability: dict[str, Any] | None = None


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    full_name: str
    first_name: str
    last_name: str
    role: str
    certifications: dict[str, Any]
    skills: dict[str, Any]
    availability: dict[str, Any]

