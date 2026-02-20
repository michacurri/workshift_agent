# System Patterns

## Architecture Overview

- **Frontend:** React + Vite SPA; pages: SubmitRequest, Approvals, Dashboard, Shiftboard (default), Consents, My Requests, AdminEmployees, Login. `api.ts` for fetch; X-Employee-Id on requests; auth via useAuth (currentUser, logout).
- **Backend:** FastAPI in `backend/main.py`; routers: schedule, partner, approval, employees, metrics, health. No business logic in route handlers—all in services.
- **LLM layer:** Abstract base in `llm/base.py`; Ollama and hosted providers; `llm/factory.py` selects by `LLM_PROVIDER` only. `parse(text, requester_context=..., reference_date=...)`; when reference_date is set, providers inject "Today's date is YYYY-MM-DD" and valid 30-day window into prompt. Used only for extraction-as-assist when user supplies text.
- **Services:** extraction_service (extract, parse_lenient, _collect_needs_input, _build_requester_context—no UUIDs in LLM context; _apply_defaults, _enforce_parsed_preconditions; _normalize_parsed_dates, SCHEDULE_WINDOW_DAYS=30 for date sanity-check; passes reference_date=today into provider.parse where today is org-local via `org_today()`); rule_engine (validation, resolve_employee, get_eligible_candidates_for_shift); scheduler_service (preview_unified uses parse_lenient for text path, returns needsInput; request_unified, list_requests, list_candidates, assign_shift, _build_summary; structured submit ensures `extraction_versions` row exists before inserting ScheduleRequest; urgent computed in org timezone); approval_service (urgent computed in org timezone); partner_service.
- **Data:** Postgres = source of truth. ScheduleRequest has requester_employee_id (NOT NULL), partner_employee_id, requester_shift_id, partner_shift_id, coverage_shift_id; status in (pending, pending_partner, pending_admin, pending_fill, partner_rejected, approved, rejected, failed). Redis = ephemeral approval tokens (TTL 900).

## Key Technical Decisions

- **Postgres for everything durable.** Redis only for approval token TTL.
- **Fingerprint idempotency:** SHA256 of canonical JSON; includes partner and shift fields for swap. Unique index on ScheduleRequest.fingerprint.
- **Normalized IDs at create:** Requester/partner employee IDs and shift IDs set when creating ScheduleRequest; approval and partner flows use these instead of re-resolving from names.
- **Status lifecycle:** swap → pending_partner → (accept) pending_admin or (reject) partner_rejected; move/cover → pending_admin or pending_fill. Approval service only acts on pending and pending_admin.
- **Transactional approval and partner actions:** UPDATE/status checks; 409 if not in expected state.
- **Unified preview/request:** One body shape (text or structured); summary returned for UI; no raw JSON as primary display.
- **48h urgent:** Computed at read time from related shift date in org timezone (`ORG_TIMEZONE`, default `America/Toronto`); unresolved statuses only; sort urgent first in list_requests and list_pending.
- **Org-time date semantics:** Date-only interpretation ("today/tomorrow", parsed-date window normalization, frontend `YYYY-MM-DD` generation) is standardized to org timezone instead of UTC.

## Design Patterns in Use

- **Dependency injection:** get_db_session, get_current_user, require_admin.
- **Factory for LLM:** Single place for provider; no conditionals elsewhere.
- **Middleware:** requestId, correlationId; AppError handler returns structured JSON.
- **Schemas:** Pydantic for API and extraction; PreviewRequestIn (one of text/structured), PreviewResponse (parsed, validation, summary, needsInput list of NeedsInputItem: field, prompt, options), ScheduleRequestOut with summary, PartnerPendingItem, ScheduleRequestListItem with urgent, ShiftCandidateOut, ShiftAssignIn.
- **Test stratification pattern:** Marker-based test lanes separate deterministic API behavior from live-provider behavior:
  - `integration` = deterministic HTTP integration tests
  - `integration_llm` = live LLM-dependent integration tests (slow, opt-in)
  Make/CI lanes are built on this marker split; frontend uses a separate deterministic Vitest lane in PR/push CI.

## Component Relationships

- **Schedule flow:** Router → SchedulerService.preview_unified / request_unified. Preview text path: ExtractionService.parse_lenient (provider.parse with reference_date=today + _collect_needs_input, which normalizes parsed dates) → if needsInput non-empty return 200 with needsInput; else apply_defaults (normalizes dates then tomorrow default), RuleEngine, _build_summary. Request text path: extract (parse with reference_date, normalize dates, full preconditions) then process_request. Structured request path: build ParsedExtraction from payload → apply_defaults → RuleEngine → ensure `extraction_versions` FK target exists → insert ScheduleRequest. Both paths use RuleEngine for validation; request path sets normalized IDs and status, writes ScheduleRequest, RequestMetrics, AuditLog, Redis when pending/pending_admin.
- **Partner flow:** Router → PartnerService; list_pending filters by status=pending_partner and partner_employee_id=current_user; accept/reject update status only (accept → pending_admin).
- **Approval flow:** Router → ApprovalService; list_pending filters pending and pending_admin, uses requester_employee_id/partner_employee_id when present; approve uses shift IDs when present (swap: two assignments); urgent computed and sorted.
- **Coverage fill:** Admin calls list_candidates (rule_engine.get_eligible_candidates_for_shift) then assign_shift (updates Shift.assigned_employee_id and matching ScheduleRequest to approved).
- **My Requests:** GET /schedule/requests → list_requests (filter by requester/partner for non-admin); items include summary, urgent; sorted urgent first.

## Critical Implementation Paths

- **SchedulerService._resolve_normalized_ids_and_status:** Sets initial status (swap→pending_partner, cover→pending_fill, move→pending_admin) and resolves partner_employee_id and shift IDs from extraction and current_user.
- **Rule engine get_eligible_candidates_for_shift:** For each employee, _validate_skill_for_shift, validate_certifications, check_shift_conflict(..., allowed_assignee_id=emp.id); include only when all pass.
- **Approval _update_status_if_pending:** WHERE status IN (pending, pending_admin); returning ScheduleRequest.
- **Seed:** Same as before; run after DB reset when new columns exist. `docker compose exec backend python -m backend.scripts.seed_db`.
- **CI execution path:** `.github/workflows/ci.yml` runs:
  - fast lane (`make test-unit`, `make test-integration-fast`) for PR/push validation
  - live-LLM lane (`make test-integration-llm`) for nightly/manual/main safety checks
