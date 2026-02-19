import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func, Computed
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base


class ShiftType(str, enum.Enum):
    morning = "morning"
    night = "night"


class RequestStatus(str, enum.Enum):
    pending = "pending"  # legacy; new requests use specific statuses below
    pending_partner = "pending_partner"
    pending_admin = "pending_admin"
    pending_fill = "pending_fill"
    partner_rejected = "partner_rejected"
    approved = "approved"
    rejected = "rejected"
    failed = "failed"


class EmployeeRole(str, enum.Enum):
    employee = "employee"
    admin = "admin"


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(Text, Computed("trim(first_name || ' ' || coalesce(last_name, ''))", persisted=True))
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[EmployeeRole] = mapped_column(
        Enum(EmployeeRole, name="employee_role"),
        default=EmployeeRole.employee,
        nullable=False,
    )
    certifications: Mapped[dict] = mapped_column(JSONB, default=dict)
    skills: Mapped[dict] = mapped_column(JSONB, default=dict)
    availability: Mapped[dict] = mapped_column(JSONB, default=dict)

    shifts: Mapped[list["Shift"]] = relationship(back_populates="assigned_employee")


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date: Mapped[date] = mapped_column(Date, index=True)
    type: Mapped[ShiftType] = mapped_column(Enum(ShiftType, name="shift_type"), index=True)
    required_skills: Mapped[dict] = mapped_column(JSONB, default=dict)
    assigned_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id"),
        nullable=True,
    )

    assigned_employee: Mapped[Employee | None] = relationship(back_populates="shifts")


class ExtractionVersion(Base):
    __tablename__ = "extraction_versions"

    version: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_used: Mapped[str] = mapped_column(String(128))
    prompt_template: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScheduleRequest(Base):
    __tablename__ = "schedule_requests"
    __table_args__ = (UniqueConstraint("fingerprint", name="uq_schedule_requests_fingerprint"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    raw_text: Mapped[str] = mapped_column(Text)
    extracted_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    raw_extraction: Mapped[dict] = mapped_column(JSONB, default=dict)
    validated_extraction: Mapped[dict] = mapped_column(JSONB, default=dict)
    extraction_version: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("extraction_versions.version"),
    )
    fingerprint: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus, name="request_status"),
        default=RequestStatus.pending,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Normalized IDs (populated at create; no name re-resolution for auth)
    requester_employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    partner_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True
    )
    requester_shift_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shifts.id"), nullable=True
    )
    partner_shift_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shifts.id"), nullable=True
    )
    coverage_shift_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shifts.id"), nullable=True
    )


class RequestMetrics(Base):
    __tablename__ = "request_metrics"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schedule_requests.id"),
        primary_key=True,
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String(255), index=True)
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

