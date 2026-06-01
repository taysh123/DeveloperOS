# DeveloperOS — TODO

_Last updated: 2026-06-01_ · Authoritative backlog. Detailed status lives in AGENT_STATE.md.

## Done (Phase 1 — Scaffolding) ✅
- [x] `devos` package skeleton: `cli.py`, `config.py`, `storage/db.py`+`schema.sql`, `providers/ai.py`, `commands/`, `core/workspace.py`, `modules/` stubs.
- [x] `pyproject.toml` (console_script `devos`), `.gitignore`, `README.md`.
- [x] `devos init` (create data dir + DB + apply schema) and `devos status` (report state).
- [x] Smoke tests in `tests/` (stdlib unittest) — 10 passing.
- [x] Initial git commit.

## Now (Phase 2 — Project Ingestion)
- [ ] Ingest service: walk files, ignore rules (.gitignore/node_modules/venv/binary/size caps), classify into buckets.
- [ ] `devos scan <path>`: persist `projects` + `files` inventory idempotently.
- [ ] `devos projects`: list registered projects.
- [ ] Tests for ingest (TDD) + docs/state updates.

## Later
- [ ] Phase 3: `devos index` / `devos search` (FTS5).
- [ ] Phase 4: `devos ask` / `devos explain`.
- [ ] Phase 5: `devos debug`.
- [ ] Phase 6: `devos task` / `devos remember` / `devos recall`.
- [ ] Phase 7: local API + React dashboard; CLI UX polish.
- [ ] Phase 8: `devos docgen`.
- [ ] Phase 9: learning & career assistants.

## Ideas / parking lot
- Real Claude AI provider behind `AIProvider`.
- Embeddings + semantic search.
- Git intelligence commands.
