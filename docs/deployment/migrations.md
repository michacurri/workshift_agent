# Database Migrations (Alembic)

## Why

Production/staging databases must not rely on `create_all` or manual resets. This project uses Alembic to evolve schema safely.

## What we have

- Alembic config: `backend/alembic.ini`
- Migration scripts: `backend/alembic/versions/`
- Baseline migration: `0001_baseline`

## Local usage

With the stack up:

```bash
make migrate
```

### Legacy dev DBs (pre-Alembic)

If your local database was created via `DEV_MODE=true` + `create_all`, it may already contain tables but no Alembic version. For the cleanest path:

- run `make db-reset` to drop volumes and recreate via migrations, then re-seed.

Create a new revision:

```bash
make migrate-revision MSG="describe change"
```

## CI/CD usage

Deploy pipelines should run:

- `alembic upgrade head`

…before rolling out the new backend version.

## Rollback policy

Prefer **roll forward** (a new migration that fixes the issue). If a rollback is required:

- restore from a Railway Postgres snapshot/backup, or
- use Alembic downgrade only if the migration is explicitly designed to be reversible.

