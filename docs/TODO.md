# DeveloperOS — TODO

_Last updated: 2026-06-11_ · Authoritative backlog. Detailed status lives in AGENT_STATE.md.

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

## Post-roadmap: Dashboard slice 10 — Design system + accessibility pass ✅
- [x] **Design tokens** in `styles.css` (single design source of truth): spacing `--space-1..6`, radii, type scale (15px body, 12px floor), motion (`--dur-fast/med` + ease, `prefers-reduced-motion` collapse), `--focus-ring`, semantic colors (`--danger/-soft`, `--success/-soft`, `--warn`); button/input/tab min-heights (44px on `pointer: coarse`), `:active` press states, 150ms transitions. **Dark-only by choice; offline system fonts (no CDN).**
- [x] **A11y pass** in `app.js`: WAI-ARIA tabs (`aria-controls` + `role="tabpanel"` + roving tabindex + Arrow/Home/End), skip link → focusable `<main>`, semantic `<footer>`, `Msg` errors → `role="alert"`, shared `Loading` primitive (`role="status"` + spinner), `ConfirmDelete` focus management + Escape, `aria-hidden` glyphs, `aria-invalid`/`aria-describedby` on add-form errors. **No new endpoints/surface; SECURITY unchanged.** D-0027. 328 tests (+10 `test_ui_static.py` contract tests), live smoke verified.

## Post-roadmap: Dashboard slice 9 — Meeting tab + v0.6.0 ✅
- [x] **Meeting** tab (the last CLI-parity gap): paste notes/transcript → grounded **summary / decisions / action items** (provider seam, mock default) + **action items → tasks bridge** (deterministic `meeting.extract_action_items` — no provider call; select/untick items; creates via the existing guarded `POST /api/tasks/create` — **no new write surface**). Transcript **never persisted** (same rule as CV text). Inline `POST /api/meeting` inherits D-0018 guards.
- [x] **v0.6.0 platform work:** `devos/providers/ollama.py` (**first real AI provider** — local daemon, stdlib `urllib`, no key, "[OLLAMA UNAVAILABLE]" graceful degradation; registered behind `providers.ai`; **default stays offline mock**); **AND-first retrieval** in `qa.retrieve` (OR fallback); **secret-aware scan** (`ingest.SECRET_FILE_PATTERNS` + `skipped_secrets`, skip-before-read); **CI** (`.github/workflows/ci.yml`, py3.11–3.13 × Linux/Windows). Version → **0.6.0**. D-0026; SECURITY §1/§2/§5/§8/§9. 318 tests (+24, incl. the CI-exposed Windows 8.3 short-path fix in `repo.find_project_for_path`), live socket smoke verified.

## Post-roadmap: Dashboard slice 8 — Career tab ✅
- [x] **Career** tab (… · Learn · **Career** · Settings): **Track a job application** (job-lead CRUD — add, inline status select, edit, two-step delete), **Interview prep** (pick a lead → grounded questions from its notes; declines when noteless), **CV match check** (paste CV + compare vs a lead's notes or a pasted description → coverage % + matched/missing keyword chips).
- [x] `GET /api/jobs` + `GET /api/jobs/interview` + `POST /api/jobs/{create,update,delete}` (in `_POST_ACTIONS`) + inline `POST /api/cv`. Reuse `repo` job CRUD + `repo.JOB_STATUSES` + `career.analyze_cv`/`interview_prep`; no new engine. **CV text treated as untrusted data, analyzed deterministically/offline, never persisted.** Inherits D-0018 guards; no schema/`server.py` change. D-0025; SECURITY §5/§9/§8. 294 tests (+22), live socket smoke verified.

## Post-roadmap: Dashboard slice 7 — CRUD polish ✅
- [x] Delete from the UI: **tasks** and **notes** (lightweight two-step confirm) and **projects** (**type-to-confirm** the project name, in a clearly-marked danger zone). Project delete is **index-only — never deletes files on disk**.
- [x] **Project pickers** on the add-task and add-note forms (dropdown of existing projects → reuses the create endpoints' existing `project` field). **Inline task-title editing** (reuses `tasks/update`).
- [x] Backend: new `repo.delete_project` (cascade via existing `ON DELETE CASCADE` FKs → files/chunks/tasks/memory, then `reconcile_fts`); `POST /api/{tasks,notes,projects}/delete` in `_POST_ACTIONS` (id-validated → 400, unknown → 404), reusing `repo.delete_task`/`delete_memory`. Inherits D-0018 CSRF/Origin/JSON/size guards; **no `server.py`/schema change**. D-0024; SECURITY §8. 272 tests (+12), live socket smoke verified.

## Post-roadmap: Dashboard slice 6 — Learning Center UI ✅
- [x] **Learn** tab (… · Projects · **Learn** · Settings): pick a file/topic + optional project + depth (Beginner/Intermediate/Advanced) → **Explain it** / **Quiz me** / **Give me exercises**, plus a **Check my understanding** box that grades a free-text answer. Reuses existing components + `AnswerBlock` (grounded text + sources, honest ungrounded note); no new CSS.
- [x] `GET /api/learn|quiz|exercise` (target required, level validated, `n` clamped 1–20/1–10) + inline `POST /api/grade` (multi-line answer; inherits D-0018 CSRF/Origin/JSON/size guards). Pure reuse of `modules/learning` (learn/quiz/exercise/grade) — no new engine; read-only, grounded with `file:line`, declines when nothing indexed matches. D-0023; SECURITY §5/§8. 260 tests (+13), live socket smoke verified.

## Post-roadmap: Dashboard slice 5 — Settings & AI Management ✅
- [x] **Settings** tab (Home · Tasks · Notes · Search & Ask · Debug · Projects · Settings): **System status** (local-first, offline, AI on/off, active provider, version, roadmap phase, projects indexed, dashboard maturity), **AI settings** (enable toggle + provider radio list with privacy/cost badges + key-detection hints), and a prepared (disabled) **provider-config** panel.
- [x] `devos/settings.py`: non-secret settings store (`settings.json`) + provider catalog (mock/ollama/claude/openai); `effective_provider_name` falls back to offline mock when disabled/unavailable; `key_present` returns a boolean only. Config/Workspace resolve provider via env → settings → mock (backward compatible).
- [x] `GET /api/system`, `GET /api/settings`, `POST /api/settings` (inline, ws-scoped; whitelists `ai_enabled`/`ai_provider` so secrets can't be stored); inherits the D-0018 CSRF/Origin/JSON/size guards. **No API keys in SQLite/JSON/frontend** — keys come from env vars; only a presence boolean is shown. D-0022; SECURITY §2/§8. Version 0.1.0→0.5.0. 247 tests (+20), live socket smoke verified (no key leak).
- [x] Authored **`docs/FUTURE_ROADMAP.md`** (product planning only): v1.0/v2.0 vision + dashboard/AI/productivity/learning/career/enterprise roadmaps + stretch goals + ideas backlog, each tagged Core/High Value/Nice-to-Have/Future Research.

## Post-roadmap: Dashboard slice 4 — Project Deep Dive / Study ✅
- [x] **Study this project** Deep Dive from project detail: Start here · Key files · How this works · Questions to explore · Interview prep + project-scoped Ask.
- [x] Read-only `GET /api/projects/study` aggregator reusing `qa.explain` + `learning.quiz` + `repo.top_files`/`category_breakdown` + deterministic offline interview checklist; id-validated, `n` clamped; no new engine. D-0021; SECURITY §8. 227 tests (+5), live smoke verified.
- [x] Recorded the long-term dashboard vision/roadmap (IA + prioritized future slices) in the plan + DECISIONS/AGENT_STATE.

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
- [ ] Dashboard (roadmap order, D-0021…D-0027): ~~Settings + AI-provider toggle~~ ✅ (slice 5), ~~Learning tab~~ ✅ (slice 6), ~~CRUD polish~~ ✅ (slice 7), ~~Career tab~~ ✅ (slice 8), ~~Meeting Summary tab~~ ✅ (slice 9, v0.6.0), ~~first real AI provider (Ollama-first)~~ ✅ (v0.6.0), ~~design-system/a11y polish~~ ✅ (slice 10), then onboarding first-run flow and Plugins/Extensions UI.
- [ ] Wire a real AI provider behind `providers.ai`: ~~Ollama~~ ✅ (v0.6.0); Claude/OpenAI remain **only if the no-cost policy changes**.
- [ ] Meeting: audio/STT (~~action-item → tasks~~ ✅ v0.6.0).
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
