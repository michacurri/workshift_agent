# Active Context

## Current Work Focus

- **Workflow cohesion v3 plan is complete (P0–P8).** The system now has normalized request ownership and shift IDs, partner consent for swaps, coverage-request semantics with admin fill, unified preview/request APIs with human-readable summaries, Shiftboard as primary UI with NL parse assist, My Requests, and 48h escalation for admins.
- **Stable areas:** Schedule request (text or structured, unified endpoints), approval (pending + pending_admin, normalized IDs when present), partner consent (pending_partner → accept/reject), coverage fill (candidates + assign, admin-only), employees CRUD with role, auth (X-Employee-Id, require_admin), Shiftboard (default tab, paste/parse, request coverage from owned shift), Consents, My Requests, Approvals with urgent highlight.

## Recent Changes (Workflow Cohesion v3)

- **P0 – Scheduler cleanup:** Fixed unreachable/duplicated code in `process_structured_request`; completed text path in `process_request` (commit, return, AuditLog, Redis). Added ErrorCode import.
- **P1–P2 – Data model:** ScheduleRequest now has `requester_employee_id` (NOT NULL), `partner_employee_id`, `requester_shift_id`, `partner_shift_id`, `coverage_shift_id`. RequestStatus extended: `pending_partner`, `pending_admin`, `pending_fill`, `partner_rejected`. IDs and initial status set at create in scheduler_service; approval_service uses IDs when present and includes pending_admin in list/update.
- **P3 – Unified API:** `POST /schedule/preview` and `POST /schedule/request` accept `PreviewRequestIn` (one of `text` or `structured`). Responses include `summary` (human-readable). `_build_summary()` in scheduler_service; ScheduleRequestOut and PreviewResponse have summary.
- **P4 – Shiftboard primary:** Default tab = Shiftboard. "Paste message" + Parse calls `previewUnified({ text })`, fills form and shows summary. Clicking an owned shift pre-fills "Request coverage" (cover + current_shift_*).
- **P5 – Partner consent:** `GET /partner/pending`, `POST /partner/{id}/accept` (→ pending_admin), `POST /partner/{id}/reject` (→ partner_rejected). Partner view shows summary and workload (shifts this week). Frontend Consents tab with accept/reject.
- **P6 – Coverage fill:** `GET /schedule/shifts/{shift_id}/candidates` (admin), `POST /schedule/shifts/{shift_id}/assign` with `{ employee_id }`. Rule engine `get_eligible_candidates_for_shift()`; assign updates shift and marks matching pending_fill request approved. My Requests (admin) shows "Fill coverage" → candidates → Assign.
- **P7 – My Requests:** `GET /schedule/requests` (employees: own + partner; admins: all). ScheduleRequestListItem with status, summary, created_at, requester_full_name, coverage_shift_id. Frontend My Requests tab.
- **P8 – 48h escalation:** `urgent` computed when related shift start is within 48h and status unresolved. List requests and pending approvals sorted urgent first; frontend shows "<48h" and red border/background on Approvals and My Requests.

## Next Steps (For New Agent)

- **DB reset (POC):** New columns on `schedule_requests` (requester_employee_id NOT NULL, etc.). Use fresh DB or migration; then run seed: `docker compose exec backend python -m backend.scripts.seed_db`.
- **Optional v2 (plan):** LLM ranking/explanations over candidate lists; iterative schedule draft generation with deterministic validation and admin approval.
- Read plan file if continuing: `~/.cursor/plans/workflow_cohesion_improvements_v3_32a608a5.plan.md`.

## Active Decisions and Preferences

- Postgres = source of truth; Redis = ephemeral approval tokens only.
- No business logic in route handlers; all in services.
- Provider selection only in `llm/factory.py`; no branching on LLM_PROVIDER elsewhere.
- Structured errors with errorCode, userMessage, developerMessage, correlationId.
- Seed script is idempotent by name for employees and by date range for shifts; re-run is safe.
- Approval list includes both `pending` and `pending_admin`; partner consent is separate (pending_partner). Coverage does not unassign requester until admin assigns a fill.

## Important Patterns and Preferences

- Read Memory Bank at start of every task (per AGENTS.md).
- On "update memory bank": review ALL memory-bank files; prioritize activeContext.md and progress.md.
- Keep documentation in sync with code (README, memory-bank) when adding endpoints, env vars, or workflows.

## Learnings and Project Insights

- Ollama cold start can exceed 5s; 60s timeout avoids false LLM_TIMEOUT on first request. Preloading with `ollama run llama3:8b` improves UX.
- Postman: use a single Content-Type (application/json) and Body type JSON to avoid malformed request/500.
- SQLAlchemy 2: Result from `update(...).returning()` has `.scalars().first()`, not `.scalar_one_or_none()`. Single-column select returns rows that need `.scalars().all()` for list of entities.
- Use `getattr(request, "requester_employee_id", None)` when reading ScheduleRequest so code tolerates older rows or migrations that add columns later.
