# Workflow Coverage Audit (JTBD / Gherkin)

This is a **traceability snapshot** of current automated tests against product workflows in `memory-bank/productContext.md`.

Status meanings:

- **Covered**: end-to-end assertions exist for the workflow's key outcomes
- **Partial**: tests exist but miss important outcomes or rely on permissive assertions/mocks
- **Missing**: no test coverage in current suite

## Workflow → Test Mapping

| Workflow | Status | Evidence |
|---|---|---|
| Employee logs in and identity persists | Covered | `frontend/src/pages/Login.test.tsx`, `frontend/src/auth.test.tsx`, `backend/tests/integration/test_auth_health_errors.py` |
| Employee submits structured move/swap/cover and gets correct status | Covered | `backend/tests/integration/test_schedule_submit.py` |
| Employee submits natural-language request (real extraction path) | Partial | `frontend/src/hooks/request.hook.test.tsx` (mocked), `backend/tests/integration/test_auth_health_errors.py` (tolerates 200/503) |
| Guided completion (`needsInput`) from preview | Partial | `frontend/src/pages/ShiftBoard.test.tsx`, `frontend/src/hooks/request.hook.test.tsx` (mocked); missing backend integration spec for `needsInput` semantics |
| Partner consent flow (pending list, accept/reject, invalid state) | Covered | `backend/tests/integration/test_partner_consent.py` |
| Admin approvals queue, approve/reject, admin-only | Covered (core) | `backend/tests/integration/test_approval.py` |
| Coverage fill workflow (candidates + assign + request approved) | Covered | `backend/tests/integration/test_coverage_fill.py`, `frontend/src/pages/MyRequests.test.tsx` |
| My Requests visibility (employee/admin), urgent semantics | Partial | `backend/tests/integration/test_my_requests.py` |
| Admin urgent highlighting in UI | Missing (frontend) | No `frontend/src/pages/Approvals.test.tsx` in current suite |
| Shiftboard primary UX (single input, review details, click shift to request coverage) | Partial | `frontend/src/pages/ShiftBoard.test.tsx`, `frontend/src/hooks/shiftBoard.hook.test.tsx` |
| Rule validation edge cases (missing employee, cert, skill mismatch, conflict) | Covered | `backend/tests/integration/test_schedule_validation.py` |
| Employees CRUD | Covered (backend), Missing (frontend) | `backend/tests/integration/test_employees_crud.py` |

## Dave’s Engineering Notes (Backend test professionalism)

Strengths:

- Tests are scenario-oriented and generally follow actor → action → expected outcome.
- Core lifecycle transitions are covered (swap/partner/admin/coverage).

Gaps:

- Some permissive assertions reduce confidence (e.g., allowing multiple status codes).
- Limited strict checks around urgency ordering and partner visibility edge cases.
- Placeholder tests were replaced with minimal real tests: unit `test_placeholder.py` now tests `time_utils.org_tz()`; integration `test_placeholder.py` now has a GET `/health` smoke test.

## Prioritized Next Tests (recommended)

Frontend:

- `frontend/src/pages/Approvals.test.tsx` — urgent-first sorting + highlight + approve/reject UX
- `frontend/src/pages/Consents.test.tsx` — partner pending list + accept/reject UX
- `frontend/src/pages/ShiftBoard.request-coverage.test.tsx` — click owned shift → prefill cover → submit
- `frontend/src/pages/ShiftBoard.nl-guided-completion.test.tsx` — `needsInput` prompt flow end-to-end (mocked API responses)
- `frontend/src/pages/AdminEmployees.test.tsx` — CRUD UX + errors

Backend:

- `backend/tests/integration/test_schedule_text_flow.py` — deterministic text-path (mock provider) for `needsInput` and success semantics
- `backend/tests/integration/test_workflow_swap_e2e.py` — employee → partner → admin lifecycle in one scenario
- `backend/tests/integration/test_urgent_ordering.py` — strict ordering guarantees for pending lists

