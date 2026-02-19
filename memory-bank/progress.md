# Progress

## What Works

- **Schedule request:** `POST /schedule/request` accepts `PreviewRequestIn` (text or structured). Text path: LLM extraction → validation → DB + Redis; structured path bypasses LLM. Idempotent by fingerprint. New requests get normalized `requester_employee_id`, optional `partner_employee_id`, shift IDs, and initial status: swap → `pending_partner`, cover → `pending_fill`, move → `pending_admin`. All responses include `summary`.
- **Unified preview:** `POST /schedule/preview` accepts text or structured; returns parsed, validation, and human-readable `summary`.
- **Approval:** GET /approval/pending (status in pending, pending_admin), POST approve/reject. Uses normalized IDs when present; approve executes swap (both shifts) or move/cover. Pending items include result_summary, full names, and `urgent` (48h). Approvals UI shows urgent highlight.
- **Partner consent:** GET /partner/pending, POST /partner/{id}/accept (→ pending_admin), POST /partner/{id}/reject (→ partner_rejected). Human-readable summary and workload (shifts this week). Consents tab with accept/reject.
- **Coverage fill:** GET /schedule/shifts/{shift_id}/candidates (admin), POST /schedule/shifts/{shift_id}/assign. Eligible candidates from rule engine (skills, certs, no conflict); assign updates shift and marks matching pending_fill request approved. My Requests (admin) shows Fill coverage → candidates → Assign.
- **My Requests:** GET /schedule/requests (employees: own + partner; admins: all). Items have status, summary, created_at, requester_full_name, coverage_shift_id, urgent. Sorted urgent first. My Requests tab.
- **Swap validation:** Rule engine validates both sides; conflict check uses allowed_assignee_id; partner resolved from extraction or from ScheduleRequest.partner_employee_id. Approval service executes swap using shift IDs when present.
- **Employees:** Full CRUD with role (employee | admin); list ordered by last_name, first_name. Seed: Priya Smith = admin. Auth: X-Employee-Id, require_admin for approval and coverage endpoints.
- **Frontend:** Login (dev select account), Submit, Approvals (urgent), Shiftboard (default tab, paste/parse, summary, request coverage from owned shift), Consents, My Requests (with Fill for admin), Dashboard, Admin (employee CRUD). All key surfaces show human-readable summaries.
- **Metrics, health, Docker, seed:** Unchanged; seed idempotent. LLM used for extraction assist only; structured-only flow works without hosted LLM.

## What's Left to Build

- **v2 (optional):** LLM ranking/explanations over deterministic candidate lists; iterative schedule draft generation with deterministic validation and admin approval (per plan).
- **DB migration/reset:** New ScheduleRequest columns require DB reset or migration for POC; then re-run seed.
- Other (optional): Circuit breaker, pagination, Alembic migrations, integration tests.

## Current Status

- **Workflow cohesion v3 (P0–P8) is complete.** Normalized IDs and statuses, unified preview/request with summary, Shiftboard primary + NL parse, partner consent, coverage fill (candidates + assign), My Requests, and 48h escalation are implemented.
- Auth (X-Employee-Id, admin role, login, scoped visibility) is in place. System is runnable with Docker + Ollama; first request may be slow until model is loaded.

## Known Issues

- None critical. If Ollama returns empty or non-JSON, EXTRACTION_INVALID_SCHEMA with developerMessage indicates the cause.
- Re-running seed deletes shifts in the seeded date range; intentional for idempotent reset.
- New ScheduleRequest columns: existing DBs need migration or reset before creating new requests.

## Evolution of Project Decisions

- **Staff redesign:** Postgres single source of truth; Redis ephemeral; fingerprint idempotency; transactional approval; versioned extraction; explicit error codes and correlation IDs.
- **Extraction schema:** partner_* and partner_shift_* for swap; requester last_name optional; requested_action swap|move|cover.
- **Auth:** Employee.role (employee | admin); X-Employee-Id; require_admin for approval and coverage; dev login; admin CRUD.
- **Workflow cohesion v3:** Normalized requester/partner/shift IDs on ScheduleRequest (no name re-resolution for auth). Status lifecycle: pending_partner → pending_admin (partner accept) or partner_rejected; pending_fill → approved when admin assigns; pending_admin → approved/rejected. Coverage = employee remains responsible until admin fills. Unified preview/request with summary; Shiftboard primary; partner consent and coverage fill endpoints and UI; My Requests; 48h urgent computed at read time, sorted and highlighted in admin UIs.
