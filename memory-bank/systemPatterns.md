# System Patterns

## Architecture Overview

- **Frontend:** React + Vite SPA; pages: SubmitRequest, Approvals, Dashboard, Shiftboard (default), Consents, My Requests, AdminEmployees, Login. `api.ts` for fetch; X-Employee-Id on requests; auth via useAuth (currentUser, logout).
- **Backend:** FastAPI in `backend/main.py`; routers: schedule, partner, approval, employees, metrics, health. No business logic in route handlers—all in services.
- **LLM layer:** Abstract base in `llm/base.py`; Ollama and hosted providers; `llm/factory.py` selects by `LLM_PROVIDER` only. Used only for extraction-as-assist when user supplies text.
- **Services:** extraction_service (parse + defaults + version); rule_engine (validation, resolve_employee, get_eligible_candidates_for_shift); scheduler_service (unified preview/request, fingerprint, normalized IDs and status, list_shifts, list_candidates, assign_shift, list_requests, _build_summary); approval_service (list_pending including pending_admin, approve/reject using normalized IDs when present, urgent); partner_service (list_pending for partner, accept/reject).
- **Data:** Postgres = source of truth. ScheduleRequest has requester_employee_id (NOT NULL), partner_employee_id, requester_shift_id, partner_shift_id, coverage_shift_id; status in (pending, pending_partner, pending_admin, pending_fill, partner_rejected, approved, rejected, failed). Redis = ephemeral approval tokens (TTL 900).

## Key Technical Decisions

- **Postgres for everything durable.** Redis only for approval token TTL.
- **Fingerprint idempotency:** SHA256 of canonical JSON; includes partner and shift fields for swap. Unique index on ScheduleRequest.fingerprint.
- **Normalized IDs at create:** Requester/partner employee IDs and shift IDs set when creating ScheduleRequest; approval and partner flows use these instead of re-resolving from names.
- **Status lifecycle:** swap → pending_partner → (accept) pending_admin or (reject) partner_rejected; move/cover → pending_admin or pending_fill. Approval service only acts on pending and pending_admin.
- **Transactional approval and partner actions:** UPDATE/status checks; 409 if not in expected state.
- **Unified preview/request:** One body shape (text or structured); summary returned for UI; no raw JSON as primary display.
- **48h urgent:** Computed at read time from related shift date; unresolved statuses only; sort urgent first in list_requests and list_pending.

## Design Patterns in Use

- **Dependency injection:** get_db_session, get_current_user, require_admin.
- **Factory for LLM:** Single place for provider; no conditionals elsewhere.
- **Middleware:** requestId, correlationId; AppError handler returns structured JSON.
- **Schemas:** Pydantic for API and extraction; PreviewRequestIn (one of text/structured), PreviewResponse, ScheduleRequestOut with summary, PartnerPendingItem, ScheduleRequestListItem with urgent, ShiftCandidateOut, ShiftAssignIn.

## Component Relationships

- **Schedule flow:** Router → SchedulerService.preview_unified / request_unified (or process_request / process_structured_request). Text path uses ExtractionService; both paths use RuleEngine, set normalized IDs and initial status, write ScheduleRequest, RequestMetrics, AuditLog, Redis when pending/pending_admin.
- **Partner flow:** Router → PartnerService; list_pending filters by status=pending_partner and partner_employee_id=current_user; accept/reject update status only (accept → pending_admin).
- **Approval flow:** Router → ApprovalService; list_pending filters pending and pending_admin, uses requester_employee_id/partner_employee_id when present; approve uses shift IDs when present (swap: two assignments); urgent computed and sorted.
- **Coverage fill:** Admin calls list_candidates (rule_engine.get_eligible_candidates_for_shift) then assign_shift (updates Shift.assigned_employee_id and matching ScheduleRequest to approved).
- **My Requests:** GET /schedule/requests → list_requests (filter by requester/partner for non-admin); items include summary, urgent; sorted urgent first.

## Critical Implementation Paths

- **SchedulerService._resolve_normalized_ids_and_status:** Sets initial status (swap→pending_partner, cover→pending_fill, move→pending_admin) and resolves partner_employee_id and shift IDs from extraction and current_user.
- **Rule engine get_eligible_candidates_for_shift:** For each employee, _validate_skill_for_shift, validate_certifications, check_shift_conflict(..., allowed_assignee_id=emp.id); include only when all pass.
- **Approval _update_status_if_pending:** WHERE status IN (pending, pending_admin); returning ScheduleRequest.
- **Seed:** Same as before; run after DB reset when new columns exist. `docker compose exec backend python -m backend.scripts.seed_db`.
