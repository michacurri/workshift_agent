# Testing Strategy

This document describes backend and frontend test strategy and how it aligns with Make targets and CI for a TDD workflow driven by user stories (e.g. from Product).

## Goals

- **Unit tests:** Fast, service-level tests that exercise business logic with a real DB/Redis (same stack as dev). No HTTP; call services directly. Isolated from external LLM.
- **Integration tests:** Run against the live API (FastAPI app) with the same stack. Use `httpx` against `http://localhost:8000` to assert full request/response and status codes.
- **Frontend unit tests:** Fast Vitest + Testing Library tests for frontend API/auth/hooks/pages using deterministic mocks (no real network).
- **CI:** One contract — backend and frontend fast lanes run deterministically on PR/push.
- **TDD:** User stories (scenarios) from Product can be turned into integration tests first, then implemented; unit tests cover service-level edge cases.

## Gherkin / JTBD Pattern

Frontend tests should include Product-readable scenario language using this format:

- **When** `[actor need / trigger]`
- **And** `[context / action input]`
- **Then** `[expected user outcome]`

Example:

- **When** an employee needs to make a change to their schedule
- **And** they enter a request in natural language
- **Then** the parser should correctly parse the request

## Layout

- **Backend tests:** `backend/tests/`
  - `conftest.py` — shared fixtures (async session, test client, base URL).
  - `unit/` — tests that import and call services/repos directly; use `@pytest.mark.unit`.
  - `integration/` — tests that call the API via HTTP; use `@pytest.mark.integration`.
- **Markers:** In `backend/pytest.ini`, `unit`, `integration`, and `integration_llm` are registered:
  - `unit`: service-level, no HTTP.
  - `integration`: HTTP/API integration tests.
  - `integration_llm`: live provider integration tests (slow, opt-in lane).

## How to Run

- **Frontend (no Docker required):**
  - `make test-frontend-unit` (repo root)
  - or in `frontend/`: `npm test`
  - optional quality gate: `npm run typecheck`
- **Stack must be up** for both unit and integration tests (they use the same Postgres/Redis as dev).
- From repo root:
  - `make test-unit` — runs `pytest -m unit` inside the backend container.
  - `make test-integration` (or `make test-integration-fast`) — runs deterministic integration tests (`integration and not integration_llm`).
  - `make test-integration-llm` — runs live-LLM integration tests only.
  - `make test-integration-all` — runs all integration tests.
  - `make test` — fast default (`not integration_llm`).
  - `make test-all` — full suite including live-LLM tests.
- From `backend/` with venv (and stack up, `DATABASE_URL`/`REDIS_URL` pointing at the stack):
  - `pytest -m unit`
  - `pytest -m "integration and not integration_llm"`
  - `pytest -m integration_llm`
  - `pytest -m "not integration_llm"` (fast default) or `pytest` (full)

## Unit Tests

- **Scope:** Rule engine, scheduler service, approval service, partner service, extraction (with mocked or no LLM). Use real DB/Redis from the compose stack.
- **Pattern:** Async fixtures that provide `AsyncSession` and (if needed) Redis; tests call service methods and assert on state or return values.
- **Speed:** No HTTP, no LLM calls; keep tests fast by avoiding unnecessary seed data (minimal fixtures per test).

## Integration Tests

- **Scope:** Full request/response for critical paths: submit request (text and structured), approval flow, partner accept/reject, coverage fill, health.
- **Pattern:** `httpx.AsyncClient` or `httpx.Client` with `base_url="http://localhost:8000"`; seed or use existing seed data; assert status codes and JSON body.
- **User stories:** When Sia provides scenarios, add them as integration tests (e.g. “Employee submits swap request → partner sees in Consents → partner accepts → admin approves”). These become the TDD spec.

## CI Hooks

- **Recommended:** Run in CI with the stack up (e.g. `docker compose up -d`, then `docker compose exec backend pytest`), or run `make test-unit` and `make test-integration` in a job that has Docker Compose available.
- **Recommended split:**
  - **PR lane:** frontend unit tests (`npm run typecheck`, `npm test` in `frontend/`)
  - **PR lane:** `make test-unit` + `make test-integration-fast`
  - **Nightly/protected lane:** `make test-integration-llm`
- **Contract:** default developer and PR runs exclude live-LLM tests; live-LLM coverage remains mandatory in a dedicated CI lane.

## Dependencies

- Test deps live in `backend/requirements-dev.txt` (pytest, pytest-asyncio, httpx). Install with `pip install -r backend/requirements-dev.txt` for local test runs, or rely on the backend image including them for `make test-*`.
