# Tech Context

## Technologies

- **Backend:** Python 3.11+, FastAPI, Uvicorn, SQLAlchemy (async), asyncpg, Redis (async), Pydantic, pydantic-settings, httpx.
- **Frontend:** React 18, Vite 5; no UI library beyond basic CSS.
- **Database:** Postgres (e.g. 16 in Docker).
- **LLM:** Local = Ollama (REST at OLLAMA_BASE_URL); Hosted = Claude-first (Anthropic API via `HOSTED_LLM_VENDOR=anthropic`, `ANTHROPIC_API_KEY`, etc.) or OpenAI fallback. Used for extraction only when user supplies text. Extraction passes reference_date (today) so prompts include "Today's date" and valid 30-day schedule window; backend normalizes parsed dates outside that window.
- **Infra:** Docker, docker-compose; Railway-compatible. Production: Alembic for schema; backend/frontend each have `railway.toml`; deploy via GitHub Actions (staging auto, production optional trigger).

## Development Setup

- **Root:** Project root is repository root; backend and frontend are sibling dirs.
- **Backend:** `backend/`; run via `uvicorn backend.main:app` or Docker. Requires `DATABASE_URL`, `REDIS_URL`, `LLM_PROVIDER`; optional Ollama/OpenAI env for LLM. Date-only semantics use `ORG_TIMEZONE` (default `America/Toronto`).
- **Frontend:** `frontend/`; `npm install` then `npm run dev`. API base URL via `VITE_API_BASE_URL`; X-Employee-Id sent when user is logged in (localStorage currentUser).
- **Frontend payloads:** Structured preview/submit normalizes optional fields (notably optional dates) so empty strings are sent as null to satisfy backend `date | None` validation.
- **First run:** `make bootstrap && make up && make migrate && make seed`. Migrations create/update tables; `DEV_MODE` is false in compose so schema is migration-owned.
- **Makefile:** Repo root has `make migrate`, `make migrate-revision MSG="..."`; stratified test commands:
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
- **Alembic:** `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/` (baseline 0001_baseline). Sync URL derived from DATABASE_URL (asyncpg → postgresql for migrations). Local: `make migrate`; new revision: `make migrate-revision MSG="..."`. Production/staging: run `alembic upgrade head` before app deploy. Legacy dev DBs: use `make db-reset` for clean migration path.

## Dependencies

- **backend/requirements.txt:** fastapi, uvicorn[standard], sqlalchemy, asyncpg, psycopg2-binary, redis, pydantic, pydantic-settings, httpx, alembic, pytest, pytest-asyncio, tzdata.
- **backend/requirements-dev.txt:** extends requirements.txt; includes ruff for lint.
- **frontend/package.json:** react, react-dom, vite (dev), serve (prod static), Vitest + React Testing Library + jsdom for frontend unit/component tests.

## Tool Usage Patterns

- **Seed DB:** `make seed` (or `docker compose exec backend python -m backend.scripts.seed_db`). Idempotent by employee name and shift date range.
- **Tests:** `make test`, `make test-unit`, `make test-integration` (stack must be up). Strategy: `docs/testing.md`.
- **Frontend tests:** `make test-frontend-unit` (or `cd frontend && npm test`), optional `cd frontend && npm run typecheck`.
- **Pytest markers:** `unit`, `integration`, and `integration_llm` (slow live-provider integration lane). `integration_llm` is excluded from fast/default test commands.
- **CI workflow:** `.github/workflows/ci.yml` defines:
  - backend-lint (Ruff), dependency-audit (pip-audit, npm audit --omit=dev --audit-level=critical), secret-scan (gitleaks with GITHUB_TOKEN)
  - frontend job: typecheck, test, build
  - fast lane (unit + integration-fast) for PR/push
  - live-LLM lane for nightly/manual/main
- **Deploy workflow:** `.github/workflows/deploy-railway.yml` — staging deploy on push to main; optional prod promotion via workflow_dispatch or AUTO_PROMOTE_PROD. See `docs/deployment/railway.md`, `docs/deployment/domains.md`, `docs/deployment/migrations.md`.
- **Config:** `backend/config.py` uses pydantic-settings. CORS via `CORS_ALLOW_ORIGINS`; port via `PORT` (Railway). Hosted LLM: `HOSTED_LLM_VENDOR=anthropic|openai`, Anthropic vars or OpenAI vars. Date-only timezone: `ORG_TIMEZONE` (default `America/Toronto`).
