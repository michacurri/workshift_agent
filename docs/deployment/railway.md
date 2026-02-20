# Railway Deployment (Staging + Production)

## Overview

This repository is a monorepo with two Railway services:

- **Backend**: FastAPI (`/backend`)
- **Frontend**: React/Vite SPA (`/frontend`)

Config-as-code:

- **Backend**: root `railway.toml` (used when backend service Root Directory is repo root). Builds with `Dockerfile.backend` so the app runs as `uvicorn backend.main:app` from `/app`.
- **Frontend**: `frontend/railway.toml`

### Monorepo: set Root Directory per service

In Railway → each service → **Settings** → **Source** → **Root Directory**:

| Service  | Root Directory |
|----------|----------------|
| Backend  | *empty* (repo root) — uses root `railway.toml` and `Dockerfile.backend` |
| Frontend | `frontend` |

The backend must build from repo root so the Dockerfile can copy `backend/` into `/app/backend/` and the `backend` package is importable. The frontend must build from `frontend/` so Nixpacks/Railpack sees a single Node app.

## Environments

Create two Railway environments:

- **staging**: default deploy target on merge to `main`
- **production**: optional promotion after staging smoke checks

## Required Railway Variables (Backend)

- **DATABASE_URL**: Railway Postgres connection string (async URL supported)
- **REDIS_URL**: Railway Redis connection string
- **DEV_MODE**: `false` in staging/prod
- **ORG_TIMEZONE**: e.g. `America/Toronto`
- **CORS_ALLOW_ORIGINS**: comma-separated allowlist (staging/prod domains)
- **LLM_PROVIDER**: `hosted`
- **HOSTED_LLM_VENDOR**: `anthropic` (Claude-first)
- **ANTHROPIC_API_KEY**
- **ANTHROPIC_MODEL**
- **ANTHROPIC_VERSION**: `2023-06-01` (unless updated)

Optional fallback:

- **HOSTED_LLM_VENDOR**: `openai`
- **OPENAI_API_KEY**, **OPENAI_BASE_URL**, **OPENAI_MODEL**

## Required Railway Variables (Frontend)

Vite requires API base URL at build time:

- **VITE_API_BASE_URL**: `https://<backend-domain>`

## CI/CD

Deployment workflow lives in `.github/workflows/deploy-railway.yml`.

### Secrets expected by the deploy workflow

- **RAILWAY_TOKEN**: Railway project token
- **RAILWAY_PROJECT_ID**
- **RAILWAY_BACKEND_SERVICE**: service name or ID
- **RAILWAY_FRONTEND_SERVICE**: service name or ID
- **STAGING_API_URL**, **STAGING_WEB_URL**
- **PROD_API_URL**, **PROD_WEB_URL**

### Promotion policy (portfolio mode)

- **Default**: staging deploy only
- **Optional**: promote to prod
  - `workflow_dispatch` input `promote_to_prod=true`, or
  - repo variable `AUTO_PROMOTE_PROD=true`

## Smoke checks

The deploy workflow smoke-checks:

- Backend: `/health`, `/health/db`, `/health/cache`
- Frontend: `/` loads

