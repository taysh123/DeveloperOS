# DeveloperOS — Decision Log

_Architectural & product decisions, newest first. Each: context · decision · rationale · status._

---

## D-0017 — Phase 9 slice 6 = Meeting/Transcript foundation (+ console-safe output)
- **Date:** 2026-06-01
- **Context:** Final enumerated Phase 9 direction: summarize a local transcript/notes file. Completes learning+career+plugin+meeting.
- **Decision:**
  - **`modules/meeting.summarize(text, *, provider, source_label)` → `MeetingSummary`** — grounded Summary/Decisions/Action-items via the provider seam; transcript is **data, not instructions**; declines (no provider call) on empty input; context capped at `MAX_TRANSCRIPT_CHARS=12000`. **No schema change; transcript not persisted (read-only).**
  - **`devos meeting summarize <file>`** (nested subcommand "foundation" namespace); reads only the user-named path with **`utf-8-sig`** (strips Windows BOM); prints summary + `Source:`.
  - **Cross-cutting fix:** `cli.main` now reconfigures stdout/stderr to **UTF-8 with replacement** (guarded; skipped for non-reconfigurable streams like test `StringIO`), so echoing non-cp1252 content (BOM, smart quotes, emoji) no longer crashes `print()` on a Windows console — benefits every content-echoing command.
- **Status:** Accepted (slice 6). All originally-enumerated Phase 9 directions now shipped; further extensions (audio STT, action-item→tasks, plugin sandboxing, CV rewrite) remain optional/on-request.

## D-0016 — Phase 9 slice 5 = Plugin / Extension Seam
- **Date:** 2026-06-01
- **Context:** Fulfil the "open architecture" goal: let external packages/opt-in local files extend DeveloperOS without forking. (Header/body of the request conflicted; user confirmed Plugin System, since Career was already shipped.)
- **Decision:**
  - **Reuse existing registries** — plugins register commands via `commands.base.register` (auto-picked by `cli.build_parser`) and AI providers via the new public `providers.ai.register_provider`. No parallel machinery, no schema change.
  - **`devos/plugins.py`:** discovery from (a) entry-point group `devos.plugins` (each resolves to a zero-arg registration callable) — always loaded; (b) `<data_dir>/plugins/*.py` — loaded **only when `DEVOS_ENABLE_LOCAL_PLUGINS=1`** (opt-in; off by default). `ensure_loaded()` runs once at `cli.main` startup, guarded; failures are isolated into `ERRORS` (never crash the CLI), successes into `LOADED`.
  - **`devos plugins`** lists loaded plugins + errors. `load_entry_point_plugins(eps=...)` accepts injected entry points for testing.
  - **Security (new surface):** loading plugins executes third-party code — a supply-chain/code-execution risk (first in the project). Entry-point plugins = packages the user installed (trusted); local `.py` are opt-in only. Documented in SECURITY.md; sandbox/signing deferred.
- **Status:** Accepted (slice 5). Remaining Phase 9 slice (meeting/transcript) deferred pending approval.

## D-0015 — Phase 9 slice 4 = Career Assistant (first slice)
- **Date:** 2026-06-01
- **Context:** First Career slice (user-approved): job-lead tracking, offline CV keyword matching, grounded interview prep — no scraping/paid APIs.
- **Decision:**
  - **Schema v4: `job_leads`** table (company/role/url/status/notes/timestamps); `schema.sql` + `MIGRATIONS[4]` + `SCHEMA_VERSION=4`; added to `db.COUNTED_TABLES` (shown in `devos status`).
  - **Job CRUD in `storage/repo`** mirroring tasks (`create_job`/`get_job`/`list_jobs`/`update_job`/`delete_job`, `JOB_STATUSES`); `devos job add/list/show/set/rm`.
  - **`modules/career.analyze_cv(cv_text, target_text)`** — deterministic, offline keyword overlap reusing `qa.question_terms` (matched/missing/coverage). `devos cv <file> [--job ID]` matches a local CV against a job's **notes** (the description; company/role excluded to avoid noise) or all jobs' notes. No AI.
  - **`career.interview_prep(conn, job_id, *, provider, n)`** — grounded interview questions from the job's stored notes via the provider seam; declines (no provider call) when the job is missing/noteless; `n` clamped [1,15]. `devos interview <job-id>`.
  - **Local-first/private:** job leads + CV text are personal data; job CRUD writes only to the local DB; `cv`/`interview` are read-only; `--file` reads only the user-named path. No scraping/external/paid APIs.
- **Status:** Accepted (Career slice 1). Remaining Phase 9 slices (plugin seam, meeting/transcript) deferred pending approval.

## D-0014 — Phase 9 slice 3 = Learning Exercises & Grading (`devos exercise` / `devos grade`)
- **Date:** 2026-06-01
- **Context:** Third narrow Phase 9 slice (user-approved), completing the Learning module's practice loop.
- **Decision:** Add `exercise()`/`Exercise` and `grade()`/`Grade` to `modules/learning.py`, reusing the shared `_resolve_chunks` + `qa.assemble_context` + provider seam. `exercise` generates `n` grounded practice tasks (default 3, clamped [1,10]). `grade` evaluates a learner's supplied answer against freshly-retrieved code (the ground truth) and returns Feedback / Strengths / Weaknesses with file:line sources. **Stateless & read-only — no persistence, no schema change** (saving scores/exercises to memory is deferred). Both decline (no provider call) when ungrounded; `grade` requires a non-empty answer (ValueError otherwise). Learner answer + code are treated as DATA, not instructions (grounding/anti-injection posture). `devos exercise`/`devos grade` reuse `ask_cmd.print_answer`.
- **Status:** Accepted (slice 3). Remaining Phase 9 slices (Career, plugin seam, meeting/transcript) still deferred pending approval.

## D-0013 — Phase 9 slice 2 = Learning Quiz (`devos quiz`)
- **Date:** 2026-06-01
- **Context:** Second narrow Phase 9 slice (user-approved), building on slice 1's Learning Assistant.
- **Decision:** Add `quiz()` + `Quiz` to `modules/learning.py` (cohesive with `learn`). Extracted the shared target→chunks logic into `_resolve_chunks` (used by both `learn` and `quiz`) — DRY, **no new retrieval logic, no schema change**. `quiz` generates `n` grounded review questions (default 5, clamped to [1,20]; `n<1` → ValueError) from file-mode or topic-mode chunks; declines (no provider call) when ungrounded; cites file:line. `devos quiz` reuses `ask_cmd.print_answer`; stdout/read-only. Same grounding/anti-injection posture as `learn`.
- **Status:** Accepted (slice 2). Remaining Phase 9 slices (career, plugin seam, meeting/transcript) still deferred pending approval.

## D-0012 — Phase 9 delivered as slices; slice 1 = Learning Assistant (`devos learn`)
- **Date:** 2026-06-01
- **Context:** Phase 9 ("future modules") is open-ended. To avoid scope creep we deliver it as **narrow, separately-approved slices**. Slice 1 (user-selected) is the Learning Assistant.
- **Decision:**
  - **`modules/learning.learn(conn, target, *, provider, level, project, limit)` → `Lesson`** gives a grounded, leveled explanation. **File mode** (target resolves to an indexed file via `repo.find_project_for_path`/`find_file_by_path`/`get_file_chunks`) grounds on that file's chunks; **topic mode** grounds via `qa.retrieve`. Declines (no provider call) when ungrounded. Same composition pattern as `debug`/`docgen` — **no new retrieval logic, no schema change.**
  - **Levels** `eli5`/`intermediate`(default)/`advanced` = different system-prompt guidance over identical grounded context. Grounding/anti-injection contract preserved (context is data; attribution from retrieval; cite file:line).
  - **`devos learn <target...>`** prints via the shared `ask_cmd.print_answer` (text + deduped file:line Sources); stdout only (read-only).
  - **Remaining Phase 9 directions (quizzes/exercises, career, plugin seam, meeting/transcript) are deferred** and require separate approval. ROADMAP Phase 9 stays in-progress (🚧), not done.
- **Status:** Accepted (slice 1).

## D-0011 — Documentation Automation: grounded docgen reusing the Q&A pipeline
- **Date:** 2026-06-01
- **Context:** Phase 8 generates project docs without a parallel pipeline, staying grounded/offline.
- **Decision:**
  - **`modules/docgen.generate(conn, doc_type, *, provider, project, limit)`** with two grounding families: code docs (`readme`/`architecture`/`api`/`setup`) ground on **`qa.retrieve`** (type-specific seed query) + project facts (`repo.category_breakdown`/`top_files`); record docs (`changelog`/`decisions`/`milestone`) ground on `repo.list_memory`/`list_tasks`. Both → `qa.assemble_context`-style context → one `provider.complete()` → `GeneratedDoc`. No new retrieval logic.
  - **Grounded / no-guess:** ungrounded types (nothing indexed / no records) return `grounded=False` with a clear message and **no provider call**.
  - **Record docs include global (project-less) memory/tasks** for the resolved project (added `include_global` to `repo.list_memory`/`list_tasks`), so user-recorded decisions surface even when not project-scoped.
  - **Output safe by default:** stdout; `--output PATH` writes but **never overwrites without `--force`** (no silent writes, SECURITY §4). Generated text is model output, never executed. Attribution (file:line / record titles) from retrieval/records, not the model.
  - Provider-agnostic via `providers.ai` (mock default); future real providers improve prose unchanged. A future dashboard/API can call `docgen.generate` directly.
- **Status:** Accepted.

## D-0010 — Dashboard: stdlib http.server local API + vendored React SPA (offline, read-only)
- **Date:** 2026-06-01
- **Context:** Phase 7 adds a dashboard. Needed a UI that stays local-first/offline/verifiable and reuses existing layers (no parallel backend), consistent with the stdlib-only ethos (D-0005).
- **Decision:**
  - **Local API = stdlib `http.server`** (`devos/api/server.py`, `ThreadingHTTPServer`), **bound to 127.0.0.1 only** and **read-only (GET)** this phase. No web framework dependency.
  - **Socket-free, testable core:** `devos/api/app.py` holds pure data builders (`overview`/`projects_payload`/`tasks_payload`/`memory_payload`/`recall_payload`) reusing `storage/repo` + `modules.recall`, and a `route(ws, path, query) -> Response` table unit-tested without binding a port; `server.py` is a thin wrapper (one live integration test).
  - **Frontend = React + `htm` (no JSX build), vendored** under `devos/api/static/vendor/` (downloaded once from unpkg, committed) → fully offline, no npm/Node, no CDN at runtime. Served as static assets (path-traversal-safe). User-selected over a full Next.js app to preserve offline/zero-build/verifiable properties.
  - **`devos serve`** runs the dashboard (loopback); `"where I left off"` is derived from the DB (latest in-progress/most-recent task + recent memory), not docs.
- **Rationale:** Ships a genuine React dashboard that is offline, dependency-free at runtime, fully testable in the existing harness, and reuses every data/service layer. Architecture stays expansion-ready (route table + loopback + read-only; future write endpoints need a token/CSRF per SECURITY §8).
- **Status:** Accepted.

## D-0009 — Task Manager & Memory: schema v3, repo CRUD, retrieval-only recall
- **Date:** 2026-06-01
- **Context:** Phase 6 activates the reserved `tasks`/`memory` tables with CRUD + cross-source recall, reusing existing layers (no parallel system, no dashboard).
- **Decision:**
  - **`tasks.priority` = TEXT `low|medium|high` (default `medium`)** — schema **v3**: `schema.sql` for fresh DBs + `MIGRATIONS[3]` ALTER for existing DBs (numbered-migration runner from D-0006-era `db.initialize`).
  - **CRUD lives in `storage/repo.py`** (matching the established SQL-in-repo pattern): `create_task/get_task/list_tasks/update_task/delete_task/search_tasks` and `create_memory/get_memory/list_memory/delete_memory/search_memory`. Commands call repo directly (CRUD is thin); orchestration (recall) is a module.
  - **`recall` (modules/recall.py) is retrieval-only and offline** — groups memory + tasks (SQL `LIKE`) with code (**reusing `qa.retrieve`** → FTS). No AI call → no new prompt-injection surface (SECURITY.md §5). Empty query lists recent memory/tasks.
  - **Tasks/memory search via SQL `LIKE`** (no new FTS table) — sufficient at single-user scale; can upgrade to FTS later.
  - **Idempotency:** `create_memory` dedups on `(project_id, title, body)` (returns existing id); task creation is additive; `update_task`/`set` operations are idempotent.
  - **Project linkage optional** (`project_id` NULL = global); resolve `--project` by name, unknown name → error.
  - **`devos task`** uses nested argparse subcommands (`add|list|show|set|rm`); thin `repo` functions keep a future API/dashboard able to call the same layer.
- **Rationale:** Delivers the Project Manager + Memory Engine on the existing schema/storage with one tiny migration, stays offline/local-first, and keeps recall safe by avoiding any model call.
- **Status:** Accepted.

## D-0008 — Debug Assistant: pluggable trace parsing + index-only location, reusing retrieval
- **Date:** 2026-06-01
- **Context:** Phase 5 turns errors/traces/logs into diagnoses. Must be useful, grounded, safe with untrusted input, and reuse existing layers (no duplicate retrieval), with no schema change.
- **Decision:**
  - **Pure, pluggable parsing in `modules/trace.py`:** `parse_python`/`parse_node`/`parse_generic` registered in `TRACE_PARSERS`; first parser yielding frames wins, else a generic `path:line` scan. New languages = new parser fn, no other change.
  - **`modules/debug.diagnose`** orchestrates: parse → **locate frames in the index only** (`repo.find_file_by_path`; absolute paths via `find_project_for_path`) → **reuse `qa.retrieve`** for related code and **`qa.assemble_context`** for context → generate via `providers.ai`.
  - **Security — no filesystem egress:** trace-supplied paths are resolved only against the DB index; DeveloperOS never opens a path named in a trace. An absolute path outside any known project is skipped. (SECURITY.md §5.)
  - **Structured, grounded output:** `DebugDiagnosis` separates deterministic evidence (`error_type`/`error_message`/`frames`/`located_frames`/`sources`) from the provider's `analysis` (system prompt mandates Observed evidence / Likely root cause / Assumptions / Recommended fix / Verification steps + file:line + low-confidence honesty). Heuristic `confidence`: high (a frame located with its code), medium (related code only), low (nothing → decline, no provider call). Attribution from parsing/retrieval, never the model.
  - **Provider readiness:** reuses the D-0007 `providers.ai` seam; real Claude/OpenAI/Ollama improve `analysis` with no debug-code change. No schema change (read-only over the index).
- **Rationale:** Delivers a safe, grounded debugger now on stdlib + mock; the parser registry and provider/retrieval reuse keep it extensible without redesign.
- **Status:** Accepted.

## D-0007 — Q&A architecture: retrieval-grounded answers via a provider seam
- **Date:** 2026-06-01
- **Context:** Phase 4 needs `ask`/`explain` that are useful but must not hallucinate, must stay local-first/offline, and must be ready for real providers later.
- **Decision:**
  - **Read-only orchestration in `modules/qa.py`:** retrieve → assemble context → generate. No schema change (Q&A reads existing index tables).
  - **Retrieval reuses `index.search`** but with **OR** semantics (new `op` param) plus a stopword filter, because natural-language questions don't co-occur as ANDed tokens. Full chunk text is loaded via `repo.get_chunk_content`.
  - **Grounding contract:** context chunks are delimited, source-tagged, and labeled as *data, not instructions* (prompt-injection posture, SECURITY.md §5). The system prompt instructs the model to answer only from context and to **decline rather than guess**. If retrieval is empty, `qa.answer` returns a decline **without calling the provider**.
  - **Attribution is computed from retrieval** (`RetrievedChunk.location` = `file:start-end`), never from the model, so provenance can't be fabricated.
  - **Provider readiness:** all generation flows through `providers.ai.get_provider()`/`complete(prompt, system=, context=)`. A real Claude/OpenAI/Ollama provider registers in `_REGISTRY` and maps (system/context/prompt) to its API — no caller changes. `MockAIProvider` stays the default (no keys). No stub providers built now (avoid dead code).
- **Rationale:** Ships honest, grounded, offline Q&A immediately; the `Answer`/`SearchHit` types + provider seam mean real models and (D-0006) semantic retrieval drop in without redesign.
- **Status:** Accepted.

## D-0006 — Indexing architecture: line-window chunks + FTS5, with a semantic seam
- **Date:** 2026-06-01
- **Context:** Phase 3 needs working keyword search now, but must not require a redesign when embedding/semantic search is added later.
- **Decision:**
  - **Chunking** is line-based, non-overlapping windows (default 50 lines), 1-based inclusive line ranges (`modules/index.chunk_text`). AST-aware chunking is deferred.
  - **Storage:** `chunks` holds metadata (line range, tags, per-chunk `content_hash`); chunk text lives only in the `chunks_fts` FTS5 table (no duplication). Each chunk carries its own `content_hash` — the future key for caching embeddings without re-chunking.
  - **Incremental reindex** is keyed on a new `files.indexed_hash` (sha256 of the indexed text). Unchanged files are skipped purely on hash equality.
  - **Search** returns a stable `SearchHit` dataclass (`modules/index.search`). Keyword (bm25) search is one strategy; a future `semantic_search` returns the same type, so callers (CLI, Phase 4 Q&A) never change. A future `embeddings(chunk_id, vector, model)` table attaches to `chunks` via `chunk_id`/`content_hash`.
  - **FTS query safety:** free text is tokenized, each token quote-escaped and wrapped, joined with implicit AND — never passed raw to `MATCH`.
- **Rationale:** Ships useful local-first search immediately with stdlib only, while the chunk model + result type form a clean seam for semantic search.
- **Status:** Accepted.

## D-0005 — Stdlib-only runtime for the foundation
- **Date:** 2026-06-01
- **Context:** The foundation must reliably run on a clean machine; network/dep friction is a risk.
- **Decision:** Phase 1 runtime depends only on the Python standard library (argparse, sqlite3, pathlib, json, unittest). Richer libraries (Typer, Rich, pytest, embeddings clients) are adopted deliberately in later phases.
- **Rationale:** Guarantees installability and testability now; keeps the foundation simple and reversible.
- **Status:** Accepted.

## D-0004 — Storage & search: local-first SQLite, FTS5 keyword search first
- **Date:** 2026-06-01
- **Context:** Single power user, daily tool, privacy matters; semantic search is desirable but heavier.
- **Decision:** Use on-device SQLite for all data; implement FTS5 keyword search first, with a design seam for embeddings/semantic search later.
- **Rationale:** Zero recurring cost, private, fast to ship; FTS5 confirmed available (SQLite 3.49.1).
- **Status:** Accepted.

## D-0003 — AI backend: provider abstraction with a mock now
- **Date:** 2026-06-01
- **Context:** AI quality matters but an API-key dependency would block foundation progress.
- **Decision:** Define an `AIProvider` interface and ship a `MockAIProvider` default; wire a real Claude provider later behind the same interface.
- **Rationale:** Whole pipeline becomes testable offline; no key needed yet; provider is swappable.
- **Status:** Accepted.

## D-0002 — Interface: CLI-first
- **Date:** 2026-06-01
- **Context:** Need a usable daily tool quickly; dashboard is the eventual portfolio centerpiece.
- **Decision:** Build the CLI (`devos ...`) first; defer the TypeScript/React dashboard to Phase 7.
- **Rationale:** Fastest path to real daily utility; the core logic the dashboard needs gets built first.
- **Status:** Accepted.

## D-0001 — Stack: Python core + TypeScript/React frontend
- **Date:** 2026-06-01
- **Context:** Need strong AI/code-parsing ecosystem plus an impressive UI eventually.
- **Decision:** Python for the core + CLI; a separate TypeScript/React dashboard added in Phase 7.
- **Rationale:** Python is best for AI/embeddings/tree-sitter; React gives a serious portfolio UI later. CLI-first keeps the two concerns cleanly separated.
- **Status:** Accepted.
