# Tech Context

## Technologies

- **Backend:** Python 3.11+, FastAPI, Uvicorn, SQLAlchemy (async), asyncpg, Redis (async), Pydantic, pydantic-settings, httpx.
- **Frontend:** React 18, Vite 5; no UI library beyond basic CSS.
- **Database:** Postgres (e.g. 16 in Docker).
- **LLM:** Local = Ollama (REST at OLLAMA_BASE_URL); Hosted = OpenAI-compatible API. Used for extraction only when user supplies text. Extraction passes reference_date (today) so prompts include "Today's date" and valid 30-day schedule window; backend normalizes parsed dates outside that window.
- **Infra:** Docker, docker-compose; Railway-compatible.

## Development Setup

- **Root:** Project root is repository root; backend and frontend are sibling dirs.
- **Backend:** `backend/`; run via `uvicorn backend.main:app` or Docker. Requires `DATABASE_URL`, `REDIS_URL`, `LLM_PROVIDER`; optional Ollama/OpenAI env for LLM. Date-only semantics use `ORG_TIMEZONE` (default `America/Toronto`).
- **Frontend:** `frontend/`; `npm install` then `npm run dev`. API base URL via `VITE_API_BASE_URL`; X-Employee-Id sent when user is logged in (localStorage currentUser).
- **Frontend payloads:** Structured preview/submit normalizes optional fields (notably optional dates) so empty strings are sent as null to satisfy backend `date | None` validation.
- **Makefile:** Repo root now has stratified test commands:
  - `make test` = fast default (`not integration_llm`)
  - `make test-all` = full suite
  - `make test-unit`
  - `make test-integration` / `make test-integration-fast` = deterministic integration lane
  - `make test-integration-llm` = live-LLM integration lane
  - `make test-integration-all` = all integration tests
  **Ollama (host):** `make ollama-serve` prints how to run Ollama on the host (`ollama serve`; use `OLLAMA_HOST=0.0.0.0:11434 ollama serve` only if backend in Docker can't connect). `make ollama-check` verifies backend can reach Ollama (requires stack up). Optional Docker Ollama: `make up-ollama`, `make ollama-pull`. See `make help` and README.
- **Docker:** `make up` runs backend, postgres, redis only. Compose uses `env_file: .env`, named volume `pgdata`. Backend has `extra_hosts: host.docker.internal:host-gateway` so it can reach host Ollama at `OLLAMA_BASE_URL=http://host.docker.internal:11434`.
- **Ollama:** Default is **host**: install Ollama, `ollama pull llama3:8b` once, then `ollama serve` in a separate terminal; `.env`: `OLLAMA_BASE_URL=http://host.docker.internal:11434`. First request after cold start can take 10–30s; backend parse timeout 60s. Production: use `LLM_PROVIDER=hosted` and hosted API.

## Technical Constraints

- Async throughout backend. Use AsyncSession and async with for DB.
- Env for secrets and provider; no hardcoded keys. `.env.example` documents vars.
- Dev mode: `DEV_MODE=true` triggers table create on startup; seed is separate.

## Schema and Migrations

- **ScheduleRequest:** Has requester_employee_id (NOT NULL), partner_employee_id, requester_shift_id, partner_shift_id, coverage_shift_id. RequestStatus enum includes pending_partner, pending_admin, pending_fill, partner_rejected.
- **ExtractionVersion FK:** ScheduleRequest.extraction_version references ExtractionVersion.version. Text submit path creates this row via ExtractionService; structured submit path must ensure the version row exists before inserting.
- **POC DB strategy:** New columns require DB reset or migration; `create_all` does not add columns to existing tables. After schema change, run seed: `docker compose exec backend python -m backend.scripts.seed_db`.

## Dependencies

- **backend/requirements.txt:** fastapi, uvicorn[standard], sqlalchemy, asyncpg, redis, pydantic, pydantic-settings, httpx, pytest, pytest-asyncio, tzdata.
- **backend/requirements-dev.txt:** extends requirements.txt for local test runs.
- **frontend/package.json:** react, react-dom, vite (dev), Vitest + React Testing Library + jsdom for frontend unit/component tests.

## Tool Usage Patterns

- **Seed DB:** `make seed` (or `docker compose exec backend python -m backend.scripts.seed_db`). Idempotent by employee name and shift date range.
- **Tests:** `make test`, `make test-unit`, `make test-integration` (stack must be up). Strategy: `docs/testing.md`.
- **Frontend tests:** `make test-frontend-unit` (or `cd frontend && npm test`), optional `cd frontend && npm run typecheck`.
- **Pytest markers:** `unit`, `integration`, and `integration_llm` (slow live-provider integration lane). `integration_llm` is excluded from fast/default test commands.
- **CI workflow:** `.github/workflows/ci.yml` defines split lanes:
  - frontend deterministic unit job (`npm run typecheck`, `npm test` in `frontend/`) for PR/push
  - fast lane (unit + integration-fast) for PR/push
  - live-LLM lane for nightly/manual/main branch events
- **Config:** `backend/config.py` uses pydantic-settings. Optional: OPENAI_*, OLLAMA_*, LLM_* timeouts and retries. Date-only timezone is configured by `ORG_TIMEZONE` (default in `.env.example`: `America/Toronto`).
