# Progress

## What Works

- **Schedule request:** `POST /schedule/request` accepts `PreviewRequestIn` (text or structured). Text path: LLM extraction → validation → DB + Redis; structured path bypasses LLM. Idempotent by fingerprint. New requests get normalized `requester_employee_id`, optional `partner_employee_id`, shift IDs, and initial status: swap → `pending_partner`, cover → `pending_fill`, move → `pending_admin`. All responses include `summary`.
- **Unified preview:** `POST /schedule/preview` accepts text or structured. Text path: lenient parse returns 200 with `parsed`, `validation`, `summary`, and optional `needsInput` (field, prompt, options) for missing date/shift type so UI can guide completion; no hard 400 for missing info. LLM receives reference date and 30-day window; parsed dates outside [today, today+30] are normalized to null so server applies "tomorrow" or cover-flow logic. Structured path unchanged. Submit still enforces full validation.
- **Structured submit (reliability):** Structured submit ensures `extraction_versions` FK target exists before inserting ScheduleRequest, preventing FK violations on `extraction_version`. Frontend also normalizes optional date fields (e.g. `partner_shift_date`) from `""` to `null` to avoid 422 parsing errors.
- **Approval:** GET /approval/pending (status in pending, pending_admin), POST approve/reject. Uses normalized IDs when present; approve executes swap (both shifts) or move/cover. Pending items include result_summary, full names, and `urgent` (48h). Approvals UI shows urgent highlight.
- **Partner consent:** GET /partner/pending, POST /partner/{id}/accept (→ pending_admin), POST /partner/{id}/reject (→ partner_rejected). Human-readable summary and workload (shifts this week). Consents tab with accept/reject.
- **Coverage fill:** GET /schedule/shifts/{shift_id}/candidates (admin), POST /schedule/shifts/{shift_id}/assign. Eligible candidates from rule engine (skills, certs, no conflict); assign updates shift and marks matching pending_fill request approved. My Requests (admin) shows Fill coverage → candidates → Assign.
- **My Requests:** GET /schedule/requests (employees: own + partner; admins: all). Items have status, summary, created_at, requester_full_name, coverage_shift_id, urgent. Sorted urgent first. My Requests tab.
- **Swap validation:** Rule engine validates both sides; conflict check uses allowed_assignee_id; partner resolved from extraction or from ScheduleRequest.partner_employee_id. Approval service executes swap using shift IDs when present.
- **Employees:** Full CRUD with role (employee | admin); list ordered by last_name, first_name. Seed: Priya Smith = admin. Auth: X-Employee-Id, require_admin for approval and coverage endpoints.
- **Frontend:** Login, Submit (previews first; directs to Shift Board if needsInput), Approvals (urgent), Shiftboard (default tab; **single input** "Describe your request or paste a message" + Preview; "Review details" optional; shows needsInput prompts when preview needs one more field; request coverage from owned shift), Consents, My Requests (with Fill for admin), Dashboard, Admin. All key surfaces show human-readable summaries.
- **Metrics, health, Docker, seed:** Unchanged; seed idempotent. LLM used for extraction assist only; structured-only flow works without hosted LLM.
- **Developer experience:** Makefile: bootstrap, up/down/restart (core services only), seed, db-reset, logs, psql, redis-cli, backend-sh, frontend-dev; **Ollama on host:** `make ollama-serve` (instructions), `make ollama-check` (verify connectivity). Optional Docker Ollama: `make up-ollama`, `make ollama-pull`. README documents: install Ollama on host, `ollama pull` once, `ollama serve`, then `make up` or `make restart`. `.env.example`: `OLLAMA_BASE_URL=http://host.docker.internal:11434`.
- **Test scaffolding:** `backend/tests/` with unit/ and integration/ markers; pytest.ini; `make test`, `make test-unit`, `make test-integration`. Strategy and TDD/CI hooks in `docs/testing.md` (user stories from Product to drive integration scenarios).
- **Test lane split implemented:** Added `integration_llm` marker and moved live-LLM error-path test into that lane. Fast/default commands exclude live-LLM tests; full suite remains available. New commands: `make test-all`, `make test-integration-fast`, `make test-integration-llm`, `make test-integration-all`.
- **CI workflow added:** `.github/workflows/ci.yml` now runs fast lane on PR/push and live-LLM lane on nightly/manual/main events.
- **Coverage permission tests stabilized:** non-admin 403 tests in coverage flow now select any available shift ID in seeded range, eliminating brittle skip conditions tied to specific seeded assignment assumptions.

## What's Left to Build

- **v2 (optional):** LLM ranking/explanations over deterministic candidate lists; iterative schedule draft generation with deterministic validation and admin approval (per plan).
- **DB migration/reset:** New ScheduleRequest columns require DB reset or migration for POC; then `make db-reset` and re-seed.
- **Tests:** Continue expanding real unit and integration coverage driven by user stories; keep deterministic tests in fast lane and LLM-dependent tests in `integration_llm` lane.
- Other (optional): Circuit breaker, pagination, Alembic migrations.

## Current Status

- **Workflow cohesion v3 (P0–P8) is complete.** Normalized IDs and statuses, unified preview/request with summary, Shiftboard primary + NL parse, partner consent, coverage fill (candidates + assign), My Requests, and 48h escalation are implemented.
- Auth (X-Employee-Id, admin role, login, scoped visibility) is in place. System is runnable with Docker + Ollama; first request may be slow until model is loaded.

## Known Issues

- None critical. If Ollama returns empty or non-JSON, EXTRACTION_INVALID_SCHEMA with developerMessage indicates the cause.
- Re-running seed deletes shifts in the seeded date range; intentional for idempotent reset.
- New ScheduleRequest columns: existing DBs need migration or reset before creating new requests.

## Evolution of Project Decisions

- **Date alignment (request target date):** LLM was returning hallucinated dates (e.g. 2023-03-16) for "tomorrow"; backend only applied server "tomorrow" when parsed.target_date was null. Fix: inject reference_date (today) and valid 30-day window into LLM prompt (Ollama + Hosted); add SCHEDULE_WINDOW_DAYS and _normalize_parsed_dates in ExtractionService so out-of-range target_date and current_shift_date are cleared before defaults/preconditions; parse() signature extended with optional reference_date.
- **Structured submit + ExtractionVersion FK:** ScheduleRequest.extraction_version references ExtractionVersion.version; structured submit bypasses ExtractionService.extract() so it must ensure the extraction version row exists before insert. Frontend sanitizes optional date fields to avoid 422s from empty strings.
- **Staff redesign:** Postgres single source of truth; Redis ephemeral; fingerprint idempotency; transactional approval; versioned extraction; explicit error codes and correlation IDs.
- **Extraction schema:** partner_* and partner_shift_* for swap; requester last_name optional; requested_action swap|move|cover.
- **Auth:** Employee.role (employee | admin); X-Employee-Id; require_admin; all admin checks use EmployeeRole.admin.
- **Workflow cohesion v3:** Normalized requester/partner/shift IDs on ScheduleRequest; status lifecycle; unified preview/request; Shiftboard primary; partner consent; coverage fill; My Requests; 48h urgent.
- **Guided completion:** Preview (text) returns 200 with needsInput instead of 400 for missing date/shift type; ExtractionService.parse_lenient + _collect_needs_input; no UUIDs in LLM context (_build_requester_context). Single input area on Shiftboard; structured form under "Review details (optional)". Production LLM: use hosted provider; Ollama is dev-only, run on host by default (make ollama-serve, ollama-check; optional make up-ollama).
- **Test operations policy:** Default dev/PR test feedback excludes live-LLM tests for speed/stability; live provider coverage remains in dedicated opt-in CI lane.
