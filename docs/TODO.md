# DeveloperOS — TODO

_Last updated: 2026-06-01_ · Authoritative backlog. Detailed status lives in AGENT_STATE.md.

## Done (Phase 1 — Scaffolding) ✅
- [x] `devos` package skeleton: `cli.py`, `config.py`, `storage/db.py`+`schema.sql`, `providers/ai.py`, `commands/`, `core/workspace.py`, `modules/` stubs.
- [x] `pyproject.toml` (console_script `devos`), `.gitignore`, `README.md`.
- [x] `devos init` (create data dir + DB + apply schema) and `devos status` (report state).
- [x] Smoke tests in `tests/` (stdlib unittest) — 10 passing.
- [x] Initial git commit.

## Done (Phase 2 — Project Ingestion) ✅
- [x] Ingest service: walk files, ignore rules (.gitignore subset/node_modules/venv/binary/size caps), classify into buckets.
- [x] `devos scan <path>`: persist `projects` + `files` inventory idempotently.
- [x] `devos projects`: list registered projects.
- [x] Tests for ingest (TDD, 15 tests) + docs/state updates.

## Done (Phase 3 — Code Indexing & Search) ✅
- [x] Index service: read recorded files, split into line-ranged chunks, store in `chunks`, mirror to `chunks_fts`.
- [x] Incremental reindex keyed on `files.indexed_hash` (empty files handled).
- [x] `devos index`: scan-then-index a project (incremental).
- [x] `devos search <query>`: bm25-ranked keyword results with file:line + snippets.
- [x] Tests for chunking + search (TDD, 20 tests) + docs/state updates + D-0006.

## Done (Phase 4 — Q&A & Project Understanding) ✅
- [x] Retrieval over the index (OR-mode `index.search` → full chunk content) → context assembly → AI provider.
- [x] `devos ask "<question>"` and `devos explain [path]` with file:line citations (mock provider, no keys).
- [x] Grounding: declines (no provider call) when retrieval is empty; never guesses.
- [x] `docs/SECURITY.md` (security-by-design) + D-0007. 21 tests (66 total).

## Done (Phase 5 — Debug Assistant) ✅
- [x] Parse errors/stack traces/logs (`modules/trace`: Python/Node/generic, pluggable); locate referenced files/lines (index-only).
- [x] Assemble context (reuse `modules/qa` retrieval) → propose cause/fix/verification via provider (`modules/debug.diagnose`).
- [x] `devos debug` (arg/--file/stdin); structured evidence + analysis + sources + confidence; declines when no evidence.
- [x] Security: index-only file location (no filesystem reads from trace paths); D-0008; SECURITY §5. 17 tests (83 total).

## Done (Phase 6 — Task Manager & Memory) ✅
- [x] Tasks CRUD with status/kind/priority/milestone/notes (schema v3 added `tasks.priority`).
- [x] Memory store (decision/summary/preference/note), idempotent create; recall across memory+tasks+code.
- [x] `devos task` (add/list/show/set/rm), `devos remember`, `devos recall`. 18 tests (103 total). D-0009.

## Now (Phase 7 — Dashboard & Polish)  _(not started — plan first)_
- [ ] Local API over existing `storage/repo` + `modules/*`; TypeScript/React (Next.js) dashboard.
- [ ] Home/overview: projects, task status, recent activity, blocked items, "where I left off".
- [ ] CLI UX polish (consider Typer/Rich).
- [ ] Phase 5: `devos debug`.
- [ ] Phase 6: `devos task` / `devos remember` / `devos recall`.
- [ ] Phase 7: local API + React dashboard; CLI UX polish.
- [ ] Phase 8: `devos docgen`.
- [ ] Phase 9: learning & career assistants.

## Ideas / parking lot
- Real Claude AI provider behind `AIProvider`.
- Embeddings + semantic search.
- Git intelligence commands.
