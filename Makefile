# Workshift Agent — developer experience
# Run from repo root. First time: make bootstrap && make up && make seed

# Use .env if present, else .env.example (e.g. before first bootstrap)
ENV_FILE := $(if $(wildcard .env),.env,.env.example)
# Core stack: backend, Postgres, Redis only. Ollama runs on host (see make ollama-serve).
COMPOSE := docker compose --env-file $(ENV_FILE)
COMPOSE_OLLAMA := $(COMPOSE) --profile ollama

.PHONY: help bootstrap up down restart ps logs logs-backend logs-db psql redis-cli backend-sh seed db-reset frontend-dev test test-all test-unit test-integration test-integration-fast test-integration-llm test-integration-all ollama-serve ollama-check up-ollama ollama-pull

help:
	@echo "Workshift Agent — common targets"
	@echo ""
	@echo "  Bootstrap (first run)"
	@echo "    make bootstrap     Create .env from .env.example if missing; install frontend deps"
	@echo ""
	@echo "  Core services (make restart = down + up)"
	@echo "    make up            Start backend, Postgres, Redis"
	@echo "    make down          Stop backend, Postgres, Redis"
	@echo "    make restart       down + up"
	@echo "    make ps            List running containers"
	@echo ""
	@echo "  Ollama (host — required for NL parsing with LLM_PROVIDER=local)"
	@echo "    make ollama-serve  Print how to run Ollama on the host"
	@echo "    make ollama-check  Verify backend can reach Ollama (requires make up)"
	@echo ""
	@echo "  Logs"
	@echo "    make logs          All services"
	@echo "    make logs-backend  Backend only"
	@echo "    make logs-db       Postgres only"
	@echo ""
	@echo "  Shells / exec"
	@echo "    make psql          Postgres psql (scheduler DB)"
	@echo "    make redis-cli     Redis CLI"
	@echo "    make backend-sh    Shell inside backend container"
	@echo ""
	@echo "  Database"
	@echo "    make seed          Run idempotent seed (employees + shifts)"
	@echo "    make db-reset      Stop stack, remove volumes, up, seed (clean state)"
	@echo ""
	@echo "  Tests (stack must be up: make up && make seed)"
	@echo "    make test          Fast default (unit + integration excluding live-LLM)"
	@echo "    make test-all      Full suite (includes live-LLM tests)"
	@echo "    make test-unit     Unit tests only (service-level)"
	@echo "    make test-integration      Integration fast lane (excludes live-LLM)"
	@echo "    make test-integration-fast Integration fast lane (explicit)"
	@echo "    make test-integration-llm  Live-LLM integration lane (slow/opt-in)"
	@echo "    make test-integration-all  All integration tests"
	@echo ""
	@echo "  Frontend (local Vite)"
	@echo "    make frontend-dev  Install deps and run Vite dev server"
	@echo ""

bootstrap:
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example"; else echo ".env already exists"; fi
	@if [ -d frontend ] && [ ! -d frontend/node_modules ]; then (cd frontend && npm install) && echo "Frontend deps installed"; fi

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

restart: down up

# --- Ollama (host). Run in a separate terminal before/after make up. ---
ollama-serve:
	@echo "Run Ollama on your host (in another terminal):"
	@echo ""
	@echo "  1. Install: https://ollama.com (or: curl -fsSL https://ollama.com/install.sh | sh)"
	@echo "  2. Pull model once: ollama pull $$(grep -E '^OLLAMA_MODEL=' $(ENV_FILE) 2>/dev/null | cut -d= -f2 || echo 'llama3:8b')"
	@echo "  3. Start server:  ollama serve"
	@echo "     (If the backend in Docker cannot reach Ollama, try: OLLAMA_HOST=0.0.0.0:11434 ollama serve)"
	@echo ""
	@echo "  Then: make up  (or make restart)"
	@echo ""

ollama-check:
	@curl -sf http://localhost:8000/health/llm >/dev/null 2>&1 && echo "Ollama reachable from backend: ok" || (echo "Ollama not reachable. Ensure: 1) Ollama running on host (make ollama-serve); 2) make up; 3) .env has OLLAMA_BASE_URL=http://host.docker.internal:11434"; exit 1)

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f

logs-backend:
	$(COMPOSE) logs -f backend

logs-db:
	$(COMPOSE) logs -f postgres

psql:
	$(COMPOSE) exec postgres psql -U user -d scheduler

redis-cli:
	$(COMPOSE) exec redis redis-cli

backend-sh:
	$(COMPOSE) exec backend /bin/sh

seed:
	$(COMPOSE) exec backend python -m backend.scripts.seed_db

db-reset: down
	$(COMPOSE) down -v
	$(COMPOSE) up -d --build
	@echo "Waiting for backend to be healthy..."
	@until $$(curl -sf http://localhost:8000/health > /dev/null 2>&1); do sleep 2; done
	$(COMPOSE) exec backend python -m backend.scripts.seed_db
	@echo "DB reset complete."

frontend-dev:
	@if [ ! -d frontend/node_modules ]; then (cd frontend && npm install); fi
	cd frontend && npm run dev

test:
	$(COMPOSE) exec backend sh -c "cd /app/backend && pytest tests -m 'not integration_llm' -v"

test-all:
	$(COMPOSE) exec backend sh -c "cd /app/backend && pytest tests -v"

test-unit:
	$(COMPOSE) exec backend sh -c "cd /app/backend && pytest tests -m unit -v"

test-integration:
	$(COMPOSE) exec backend sh -c "cd /app/backend && pytest tests -m 'integration and not integration_llm' -v"

test-integration-fast:
	$(COMPOSE) exec backend sh -c "cd /app/backend && pytest tests -m 'integration and not integration_llm' -v"

test-integration-llm:
	$(COMPOSE) exec backend sh -c "cd /app/backend && pytest tests -m integration_llm -v"

test-integration-all:
	$(COMPOSE) exec backend sh -c "cd /app/backend && pytest tests -m integration -v"

# Optional: run Ollama in Docker instead of on host (set OLLAMA_BASE_URL=http://ollama:11434 in .env)
up-ollama:
	$(COMPOSE_OLLAMA) up -d --build

ollama-pull:
	$(COMPOSE_OLLAMA) exec -T ollama ollama pull $${OLLAMA_MODEL:-llama3:8b}
