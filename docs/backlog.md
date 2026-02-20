# Backlog / Pinned Items

## Pinned: LLM-edge test strictness

We currently have at least one integration test that intentionally tolerates either `200` (LLM available) or `503` (LLM unavailable) for the text preview path.

This is acceptable for portfolio launch while infra is stabilizing, but it is **not** a production-grade contract test yet.

Future improvement:

- Convert to deterministic hosted-mock tests for the text parsing path (guaranteed success/needsInput/error taxonomy).
- Keep a dedicated nightly lane for live-LLM integration behavior with strict assertions and explicit vendor config.

