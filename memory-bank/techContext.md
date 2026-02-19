# Tech Context

## Technologies

- **Backend:** Python 3.11+, FastAPI, Uvicorn, SQLAlchemy (async), asyncpg, Redis (async), Pydantic, pydantic-settings, httpx.
- **Frontend:** React 18, Vite 5; no UI library beyond basic CSS.
- **Database:** Postgres (e.g. 16 in Docker).
- **LLM:** Local = Ollama (REST at OLLAMA_BASE_URL); Hosted = OpenAI-compatible API. Used for extraction only when user supplies text.
- **Infra:** Docker, docker-compose; Railway-compatible.

## Development Setup

- **Root:** Project root is repository root; backend and frontend are sibling dirs.
- **Backend:** `backend/`; run via `uvicorn backend.main:app` or Docker. Requires `DATABASE_URL`, `REDIS_URL`, `LLM_PROVIDER`; optional Ollama/OpenAI env for LLM.
- **Frontend:** `frontend/`; `npm install` then `npm run dev`. API base URL via `VITE_API_BASE_URL`; X-Employee-Id sent when user is logged in (localStorage currentUser).
- **Docker:** `docker compose up --build` runs backend, postgres, redis. Backend may use `host.docker.internal` for Ollama when LLM_PROVIDER=local.
- **Ollama:** Run `ollama serve`; optionally preload model. First request after cold start can take 10–30s; backend parse timeout 60s by default.

## Technical Constraints

- Async throughout backend. Use AsyncSession and async with for DB.
- Env for secrets and provider; no hardcoded keys. `.env.example` documents vars.
- Dev mode: `DEV_MODE=true` triggers table create on startup; seed is separate.

## Schema and Migrations

- **ScheduleRequest:** Has requester_employee_id (NOT NULL), partner_employee_id, requester_shift_id, partner_shift_id, coverage_shift_id. RequestStatus enum includes pending_partner, pending_admin, pending_fill, partner_rejected.
- **POC DB strategy:** New columns require DB reset or migration; `create_all` does not add columns to existing tables. After schema change, run seed: `docker compose exec backend python -m backend.scripts.seed_db`.

## Dependencies

- **backend/requirements.txt:** fastapi, uvicorn[standard], sqlalchemy, asyncpg, redis, pydantic, pydantic-settings, httpx.
- **frontend/package.json:** react, react-dom, vite (dev).

## Tool Usage Patterns

- **Seed DB:** From repo root or in container: `python -m backend.scripts.seed_db` (needs DATABASE_URL). Idempotent by employee name and shift date range.
- **Config:** `backend/config.py` uses pydantic-settings. Optional: OPENAI_*, OLLAMA_*, LLM_* timeouts and retries.
