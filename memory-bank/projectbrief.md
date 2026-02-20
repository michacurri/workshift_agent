# Project Brief: Shift Scheduler Agent

## Purpose

Build a **production-ready, hybrid LLM workflow agent** that accepts natural language or structured shift-change requests, extracts via LLM when text is supplied, validates via a deterministic rule engine, and supports partner consent (swaps) and admin approval/fill (coverage)—with normalized request ownership, human-readable summaries, and full audit and metrics. LLM is extraction-as-assist only; provider swappable (local vs hosted) via configuration.

## Core Requirements

- **Input:** Natural language or structured (unified endpoints). Text triggers LLM extraction; structured bypasses LLM.
- **Extraction:** LLM parses free text when supplied; Pydantic validation and deterministic defaults. Preview returns human-readable summary and optional needsInput (guided completion); no stable identifiers (UUIDs) sent to LLM.
- **Validation:** Deterministic rule engine only. Checks: employee exists, skill match, certifications, shift conflict; returns valid, errorCodes, suggestions. No LLM in rules.
- **State:** Postgres = source of truth. ScheduleRequest has normalized requester/partner/shift IDs; status: pending_partner, pending_admin, pending_fill, partner_rejected, approved, rejected. Redis = ephemeral approval tokens (TTL 900s).
- **Workflows:** Swap → pending_partner (partner accept → pending_admin); coverage → pending_fill until admin assigns; move → pending_admin. Approve/reject transactional; 409 if not pending/pending_admin.
- **Idempotency:** Fingerprint (canonical hash, including partner/shift for swap) returns existing record on duplicate submit.
- **Observability:** Logging with requestId/correlationId; health and metrics; error taxonomy. Urgent (<48h to shift) computed at read time and highlighted in admin UIs.
- **Provider swap:** LLM_PROVIDER=local|hosted; single factory; no conditionals elsewhere.

## Scope (In Scope)

- Backend: FastAPI, SQLAlchemy async, Postgres, Redis, Pydantic, env-driven config.
- LLM: Extraction only (Ollama or hosted); strict JSON schema; used when user supplies text.
- Services: Extraction, rule engine, scheduler (unified preview/request, normalized IDs, list_requests, candidates, assign), approval (pending + pending_admin), partner (consent accept/reject).
- API: Schedule preview and request (unified), shifts, schedule/requests, shift candidates and assign (admin), partner pending/accept/reject, approval pending/approve/reject, metrics, health, employees CRUD.
- Frontend: React + Vite—Login, Submit, Shiftboard (primary, paste/parse, request coverage), Consents, My Requests, Approvals (urgent), Dashboard, Admin (employee CRUD). Auth: X-Employee-Id; admin-only for approval and coverage fill.
- Infra: Docker Compose, seed script, README, AGENTS.md Memory Bank. Production: Railway (staging + production), Alembic migrations, CI/CD via GitHub Actions.

## Out of Scope (Unless Added Later)

- Circuit breaker, background task queue, pagination.
- **v2 (optional):** LLM ranking over candidates; iterative schedule draft generation with deterministic validation.

## Success Criteria

- Submit text or structured → validation and summary; correct initial status (pending_partner, pending_admin, pending_fill).
- Swap: partner consent then admin approval; coverage: admin fill via candidates and assign. My Requests and Approvals show urgent first with highlight.
- Duplicate submit → idempotent. Approve/reject → transactional; 409 if not pending. LLM_PROVIDER switch requires no code changes.
