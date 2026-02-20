"""Baseline schema.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-02-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enums
    employee_role = postgresql.ENUM("employee", "admin", name="employee_role", create_type=False)
    shift_type = postgresql.ENUM("morning", "night", name="shift_type", create_type=False)
    request_status = postgresql.ENUM(
        "pending",
        "pending_partner",
        "pending_admin",
        "pending_fill",
        "partner_rejected",
        "approved",
        "rejected",
        "failed",
        name="request_status",
        create_type=False,
    )
    employee_role.create(op.get_bind(), checkfirst=True)
    shift_type.create(op.get_bind(), checkfirst=True)
    request_status.create(op.get_bind(), checkfirst=True)

    # Tables
    op.create_table(
        "employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "full_name",
            sa.Text(),
            sa.Computed("trim(first_name || ' ' || coalesce(last_name, ''))", persisted=True),
            nullable=False,
        ),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("last_name", sa.String(length=255), nullable=False),
        sa.Column("role", employee_role, nullable=False, server_default="employee"),
        sa.Column("certifications", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("availability", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "shifts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("type", shift_type, nullable=False),
        sa.Column("required_skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("assigned_employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=True),
    )
    op.create_index("ix_shifts_date", "shifts", ["date"])
    op.create_index("ix_shifts_type", "shifts", ["type"])

    op.create_table(
        "extraction_versions",
        sa.Column("version", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("model_used", sa.String(length=128), nullable=False),
        sa.Column("prompt_template", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "schedule_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("extracted_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("raw_extraction", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("validated_extraction", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("extraction_version", sa.String(length=64), sa.ForeignKey("extraction_versions.version"), nullable=False),
        sa.Column("fingerprint", sa.String(length=128), nullable=False),
        sa.Column("status", request_status, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("requester_employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("partner_employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("requester_shift_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shifts.id"), nullable=True),
        sa.Column("partner_shift_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shifts.id"), nullable=True),
        sa.Column("coverage_shift_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shifts.id"), nullable=True),
        sa.UniqueConstraint("fingerprint", name="uq_schedule_requests_fingerprint"),
    )
    op.create_index("ix_schedule_requests_fingerprint", "schedule_requests", ["fingerprint"])
    op.create_index("ix_schedule_requests_status", "schedule_requests", ["status"])

    op.create_table(
        "request_metrics",
        sa.Column("request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schedule_requests.id"), primary_key=True, nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_table("request_metrics")

    op.drop_index("ix_schedule_requests_status", table_name="schedule_requests")
    op.drop_index("ix_schedule_requests_fingerprint", table_name="schedule_requests")
    op.drop_table("schedule_requests")

    op.drop_table("extraction_versions")

    op.drop_index("ix_shifts_type", table_name="shifts")
    op.drop_index("ix_shifts_date", table_name="shifts")
    op.drop_table("shifts")

    op.drop_table("employees")

    bind = op.get_bind()
    postgresql.ENUM(name="request_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="shift_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="employee_role").drop(bind, checkfirst=True)

