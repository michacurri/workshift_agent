# Active Context

## Current Work Focus

- **Workflow cohesion v3 (P0–P8) plus UX refinements.** System has normalized request ownership and shift IDs, partner consent, coverage fill, unified preview/request, Shiftboard as primary UI with **single input area** ("Describe your request or paste a message"), **guided completion** (preview returns `needsInput` instead of hard errors for missing date/shift type), and Ollama running **on host** (not in Docker by default).
- **Stable areas:** Schedule request (text or structured), approval, partner consent, coverage fill, employees CRUD, auth, Shiftboard (single input + Preview, "Review details" optional), Consents, My Requests, Approvals with urgent highlight. Preview returns parsed + validation + summary + optional `needsInput` for missing fields.

## Recent Changes (Post–v3 UX and DX)

- **Frontend unit testing baseline added (Vitest + RTL + jsdom):** `frontend/package.json` now includes `test`, `test:watch`, `test:coverage`, and `typecheck` scripts with Vitest + Testing Library dependencies. `frontend/vite.config.ts` now includes test config (`jsdom`, setup file, coverage defaults). Shared deterministic setup is in `frontend/src/test/setup.ts`.
- **Gherkin/JTBD test language established for frontend:** New frontend tests use Product-readable scenario naming (`When / And / Then`) to map engineering assertions directly to jobs-to-be-done.
- **Frontend test coverage added across high-signal areas:**
  - API/auth unit tests: `frontend/src/api.test.ts`, `frontend/src/auth.test.tsx`
  - Hook tests: `frontend/src/hooks/request.hook.test.tsx`, `frontend/src/hooks/approvals.hook.test.tsx`, `frontend/src/hooks/shiftBoard.hook.test.tsx`
  - Component tests: `frontend/src/pages/Login.test.tsx`, `frontend/src/pages/MyRequests.test.tsx`, `frontend/src/pages/ShiftBoard.test.tsx`
- **Frontend typing fix:** `frontend/src/pages/Login.tsx` now sets `first_name` and `last_name` in `setCurrentUser(...)` to match `CurrentUser` type requirements.
- **CI/Make/docs wiring for frontend tests:** Added `make test-frontend-unit`, CI job `Frontend Unit Tests` in `.github/workflows/ci.yml`, and frontend + Gherkin guidance in `docs/testing.md`.

- **Date mismatch fix:** Requests like "I need my shift covered tomorrow" now get the correct target date (aligned with seed). LLM was returning hallucinated dates (e.g. 2023-03-16); backend only applied "tomorrow" when parsed.target_date was null. Fix: (1) **LLM prompt** — `parse()` accepts optional `reference_date`; both Ollama and Hosted providers inject "Today's date is YYYY-MM-DD", "Valid scheduling window is today through 30 days", and "For relative dates like 'tomorrow' use today + 1 day; prefer null if uncertain." (2) **Server-side validation** — `ExtractionService` uses `SCHEDULE_WINDOW_DAYS = 30`, `_is_date_in_window()`, and `_normalize_parsed_dates(parsed, today)` to clear `target_date` and `current_shift_date` when outside [today, today+30]. Normalization runs in `extract()` (before preconditions), `_collect_needs_input()`, and `_apply_defaults()`, so out-of-range LLM dates are treated as missing and server applies tomorrow or cover-flow logic.
- **Cover shift alignment:** For cover requests, backend aligns `current_shift_date`/`current_shift_type` to the shift being covered (the `target_*` shift) so "tomorrow" maps consistently across parsed/validated/structured flows.
- **Structured submit stability:** `POST /schedule/request/structured` now ensures the `extraction_versions` FK target exists (structured path bypassed `ExtractionService.extract()` which creates the version row). This prevents DB FK violations when inserting ScheduleRequest with `extraction_version` set.
- **Frontend payload sanitation:** Structured submit/preview now converts optional date fields like `partner_shift_date` from `""` to `null` before sending, preventing 422 date parsing errors.
- **DB constraint UX:** Unhandled DB `IntegrityError` no longer presents as browser "Failed to fetch"; backend returns a structured 409 with `DB_ERROR` so UI shows a real error message.
- **Guided completion:** `POST /schedule/preview` with text uses `ExtractionService.parse_lenient()`; returns 200 with best-effort `parsed`, `validation`, `summary`, and `needsInput` (field, prompt, options) so UI can ask for one missing piece (e.g. "What date?") instead of failing. Schemas: `PreviewResponse.needsInput`, `NeedsInputItem`. Submit still requires valid payload; preview never 400s for "missing info" on text path.
- **Single input UX:** Shiftboard has one primary textarea "Describe your request (or paste a message)" + Preview; structured form is under collapsible "Review details (optional)". SubmitRequest page previews first and directs user to Shift Board if `needsInput` present.
- **LLM context security:** No UUIDs or other stable identifiers sent to LLM. `ExtractionService._build_requester_context()`: hosted provider gets only "Interpret I/me/my as requester"; local (Ollama) may include requester name, never ID.
- **Role checks:** All admin checks use `EmployeeRole.admin` (fixed `schedule.py` list_shifts and `scheduler_service._enforce_requester_matches_current_user`).
- **Ollama on host (default):** Makefile runs core services only (backend, postgres, redis). Developer runs Ollama on host: `ollama serve` (or `OLLAMA_HOST=0.0.0.0:11434 ollama serve` only if backend in Docker can't reach it). `make ollama-serve` prints steps; `make ollama-check` verifies backend can reach Ollama. `.env`: `OLLAMA_BASE_URL=http://host.docker.internal:11434`. Optional Docker Ollama: `make up-ollama`, `make ollama-pull`.
- **Ollama model-not-found:** When Ollama returns 404 with "model not found", backend returns 503 with clear user message; `/health/llm` checks that configured model is installed and returns fail otherwise.
- **Test-lane stratification (fast vs live-LLM):** Added pytest marker `integration_llm` for live provider integration tests, tagged `test_llm_error_returns_503_with_message` with `@pytest.mark.integration_llm`, and split Make targets into fast/default vs full/LLM lanes:
  - `make test` now runs fast default (`pytest -m 'not integration_llm'`)
  - `make test-all` runs full suite
  - `make test-integration` and `make test-integration-fast` run `integration and not integration_llm`
  - `make test-integration-llm` runs only live-LLM tests
  - `make test-integration-all` runs all integration tests
- **CI lanes added:** New workflow `.github/workflows/ci.yml`:
  - **test-fast** job for PR/push (non-scheduled): unit + fast integration
  - **test-integration-llm** job for nightly/manual/main: live-LLM integration lane
- **Coverage permission tests de-flaked:** Non-admin 403 coverage tests now use any available shift id from seeded range (instead of brittle John/day-specific lookup), removing skip-only behavior from expected permission assertions.

## Next Steps (For New Agent)

- **Optional v2 (plan):** LLM ranking/explanations over candidate lists; iterative schedule draft generation with deterministic validation and admin approval.
- **DB:** After schema changes, `make db-reset` or migration then `make seed`. Seed does not create ScheduleRequest rows; add demo requests in seed if needed for Fill coverage demos.
- **CI hardening (optional):** If hosted provider credentials are not present in CI, keep `integration_llm` lane pointing at local Ollama setup or gate lane execution on secrets availability.

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

- **Date handling:** Shifts are only ever in the future; schedule window is 30 days (configurable via `SCHEDULE_WINDOW_DAYS`). Giving the LLM "today" and the valid window in the prompt reduces hallucinated dates; normalizing out-of-range parsed dates server-side guarantees alignment with seed and user intent ("tomorrow" → today+1).
- Ollama cold start can exceed 5s; 60s timeout avoids false LLM_TIMEOUT on first request. Preloading with `ollama run llama3:8b` improves UX.
- **Ollama on host:** Plain `ollama serve` often works with Docker backend (e.g. macOS). Use `OLLAMA_HOST=0.0.0.0:11434 ollama serve` only when the backend container cannot reach the host (e.g. some WSL2/Linux setups).
- Postman: use a single Content-Type (application/json) and Body type JSON to avoid malformed request/500.
- SQLAlchemy 2: Result from `update(...).returning()` has `.scalars().first()`, not `.scalar_one_or_none()`. Single-column select returns rows that need `.scalars().all()` for list of entities.
- Use `getattr(request, "requester_employee_id", None)` when reading ScheduleRequest so code tolerates older rows or migrations that add columns later.
