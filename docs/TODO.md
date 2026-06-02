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

## Done (Phase 7 — Dashboard & Polish) ✅
- [x] Local API (`devos/api`, stdlib http.server, loopback, read-only) over existing repo/modules.
- [x] React+htm SPA (vendored offline): overview, task status, blocked, recent activity, "where I left off", recall search.
- [x] `devos serve`; static serving traversal-safe; 12 tests (115 total). D-0010, SECURITY §8.

## Done (Phase 8 — Documentation Automation) ✅
- [x] `devos docgen <type>`: readme / architecture / api / setup / changelog / decisions / milestone.
- [x] Grounded via `modules/qa` retrieval (code docs) + memory/tasks (record docs); declines when ungrounded.
- [x] stdout default; `--output` no-clobber + `--force`. 11 tests (126 total). D-0011.

## Phase 9 — Future Modules (narrow slices)
### Done
- [x] Slice 1 — Learning Assistant: `devos learn <path|topic> [--level eli5|intermediate|advanced]` (grounded, cites file:line, declines). 7 tests. D-0012.
- [x] Slice 2 — Learning Quiz: `devos quiz <path|topic> [--n N]` (n grounded questions, declines). 7 tests (140 total). D-0013.
- [x] Slice 3 — Exercises & Grading: `devos exercise` (n grounded tasks) + `devos grade` (answer eval). 11 tests (151 total). D-0014.
- [x] Slice 4 — Career Assistant (1st): `devos job` + `devos cv` + `devos interview` (schema v4 `job_leads`). 16 tests. D-0015.
- [x] Slice 5 — Plugin/Extension seam: `devos plugins`; entry-point + opt-in local plugins. 8 tests. D-0016.
- [x] Slice 6 — Meeting/Transcript: `devos meeting summarize <file>` (grounded) + console-safe UTF-8 output. 7 tests (183 total). D-0017.

## Post-roadmap: Dashboard slice 3 — Debug Assistant tab ✅
- [x] Debug tab: paste an error/stack trace/log → Analyze → result cards (summary + confidence, plain-language cause/fix, related files, sources).
- [x] `POST /api/debug` (read-only) reuses `modules/debug.diagnose`; inline in `route()`; trace = untrusted data, file location index-only, not persisted; inherits slice-1 CSRF/Origin/size guards. D-0020; SECURITY §5/§8. 222 tests (+6), live smoke verified.

## Post-roadmap: Dashboard slice 2 — Projects tab ✅
- [x] Projects tab (Home · Tasks · Notes · Search & Ask · Projects): list, detail, and a safe import/scan flow (confirm-before-write).
- [x] GET `/api/projects/detail` (overview: file count, last scanned, indexed status, category breakdown) + POST `/api/projects/scan` (validate path → `ingest.scan_project` → `index_mod.index_project`).
- [x] Reuses existing scan/index/repo; untrusted path validated server-side; inherits slice-1 CSRF/Origin/loopback guards. D-0019; SECURITY §8. 216 tests (+8), live smoke verified.

## Post-roadmap: Dashboard action slice 1 ✅
- [x] Action-oriented, tabbed dashboard (Home · Tasks · Notes · Search & Ask): create/update tasks, add/edit notes, code search, plain-English Q&A — all from the UI.
- [x] Guarded write API: POST `tasks/notes create|update` reusing repo writes; GET `search`/`ask`/`explain` reusing `index`/`qa`. `repo.update_memory` added.
- [x] Security: CSRF token (`X-DevOS-Token` via `/api/session`) + Origin allowlist + JSON-only + 64 KB cap, no CORS, loopback-only. D-0018; SECURITY §8 NOW. 208 tests (+25), live smoke verified.

## All roadmap phases (0–9) shipped their planned scope. Optional future extensions (on request only)
- [ ] Dashboard: learning/career/meeting tabs, task/note/project delete (with confirm) + project pickers in forms.
- [ ] Wire a real AI provider (Claude/OpenAI/Ollama) behind `providers.ai`.
- [ ] Meeting: audio/STT, action-item → tasks.
- [ ] Plugin sandboxing/permissions/signing; plugin marketplace.
- [ ] Career: CV rewrite/cover-letter; (scraping/APIs intentionally excluded).
- [ ] Semantic/embedding search (D-0006 seam); persisted exercises/scores; multi-user/cloud sync.
- [ ] Phase 5: `devos debug`.
- [ ] Phase 6: `devos task` / `devos remember` / `devos recall`.
- [ ] Phase 7: local API + React dashboard; CLI UX polish.
- [ ] Phase 8: `devos docgen`.
- [ ] Phase 9: learning & career assistants.

## Ideas / parking lot
- Real Claude AI provider behind `AIProvider`.
- Embeddings + semantic search.
- Git intelligence commands.
