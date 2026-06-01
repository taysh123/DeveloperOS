# DeveloperOS — Architecture

_Last updated: 2026-06-01_

## Guiding principles
- **Local-first**: all data on-device in SQLite under a per-machine data dir.
- **Layered & open**: thin CLI → service/module layer → storage + providers. New
  modules and interfaces (dashboard, API, plugins) attach without rewrites.
- **Stdlib-first runtime**: the foundation depends only on the Python standard
  library so it runs on a clean machine; heavier libraries are adopted deliberately.
- **Provider abstraction**: AI is behind an interface; a mock is the default until a
  real Claude provider is wired in.
- **Safety**: no destructive or outward-facing action without explicit confirmation.

## High-level layers
```
            ┌─────────────────────────────────────────────┐
 Interfaces │  CLI (devos)   ·   [later] Local API + React  │
            └───────────────┬─────────────────────────────┘
                            │ calls
            ┌───────────────▼─────────────────────────────┐
  Modules   │ brain · codemap · debug · tasks · memory ·   │
 (services) │ search · docgen · action · git · automation  │
            └───────────────┬─────────────────────────────┘
              uses          │            uses
        ┌───────────────────▼───────┐   ┌───────────────────────┐
 Core   │ config · workspace · paths │   │ providers/ai (Mock|…) │
        └───────────────┬───────────┘   └───────────────────────┘
                        │ persists
            ┌───────────▼───────────────┐
 Storage    │  SQLite (schema + FTS5)    │
            └────────────────────────────┘
```

## Package layout (target)
```
devos/                      # Python package (core + CLI)
  __init__.py               # version, package metadata
  __main__.py               # `python -m devos`
  cli.py                    # argparse CLI: dispatch to commands
  config.py                 # paths, data dir, settings (env-overridable)
  commands/                 # one module per CLI command group
    __init__.py
    base.py                 # Command protocol / registry
    init_cmd.py             # `devos init`
    status_cmd.py           # `devos status`
  core/
    __init__.py
    workspace.py            # project registry & "current project" context
  storage/
    __init__.py
    db.py                   # connection factory, migrations, schema
    schema.sql              # declarative schema (projects, files, tasks, memory, fts)
  modules/                  # product modules, filled in per phase (stubs first)
    __init__.py
  providers/
    __init__.py
    ai.py                   # AIProvider ABC + MockAIProvider + factory
docs/                       # source of truth (this folder)
tests/                      # unittest-based (stdlib), pytest-compatible
  test_smoke.py
pyproject.toml              # packaging, console_script: devos
README.md
.gitignore
```

## Data model (initial schema)
SQLite database at the data dir (`<data>/devos.db`). Tables grow per phase; the
foundation creates the spine:

- **projects** — `id, name, root_path, created_at, last_scanned_at, meta(json)`.
- **files** — `id, project_id, rel_path, lang, category, size, content_hash, indexed_hash, indexed_at`
  (category ∈ frontend/backend/db/api/auth/test/config/other; `content_hash` = scan-time state,
  `indexed_hash` = sha256 of the text the current chunks were built from, for incremental reindex).
- **chunks** — `id, file_id, start_line, end_line, tags, content_hash` (Phase 3). `content_hash`
  is per-chunk — the future cache key for embeddings.
- **chunks_fts** — FTS5 virtual table holding chunk text; bm25-ranked keyword search (Phase 3).
  Mirrored manually on insert/delete; `repo.reconcile_fts` sweeps orphans after cascade deletes.
- **tasks** — `id, project_id, title, kind(task|bug|feature), status, milestone, notes, created_at, updated_at` (Phase 6).
- **memory** — `id, project_id, kind, title, body, tags, created_at` (Phase 6).
- **schema_migrations** — applied migration versions (foundation).

A lightweight versioned migration runner (`storage/db.py`, `PRAGMA user_version`) builds
fresh databases from `schema.sql` and upgrades existing ones via numbered `MIGRATIONS`;
re-running is safe. Current schema version: **v2** (added `files.indexed_hash`).

### Search & the semantic seam
`modules/index` owns chunking, incremental indexing, and search. `search()` returns a
stable `SearchHit` type; today's strategy is FTS5 keyword (bm25) search. A future
semantic strategy will return the **same** `SearchHit`, so callers (CLI, Phase 4 Q&A)
need no change. Per-chunk `content_hash` lets a later `embeddings(chunk_id, vector, model)`
table attach to chunks without re-chunking. See DECISIONS.md D-0006.

### Q&A & understanding (`modules/qa`)
`modules/qa` is read-only orchestration: **retrieve** (OR-mode `index.search` + full chunk
text) → **assemble** a delimited, source-tagged context → **generate** via `providers/ai`.
Answers are **grounded**: attribution (`file:line`) comes from retrieval, the system prompt
forbids guessing, and an empty retrieval returns a decline without calling the provider.
Generation is provider-agnostic (`get_provider()`/`complete(prompt, system=, context=)`),
so real Claude/OpenAI/Ollama providers slot in without caller changes. Context is treated as
untrusted data (prompt-injection posture — see SECURITY.md §5). See DECISIONS.md D-0007.

### Plugin / extension seam (`devos/plugins.py`, Phase 9 slice 5)
`cli.main` calls `plugins.ensure_loaded()` at startup. Plugins extend DeveloperOS through the
**existing** registries — commands via `commands.base.register` (auto-included by `build_parser`)
and AI providers via `providers.ai.register_provider`. Sources: entry-point group `devos.plugins`
(always) and `<data_dir>/plugins/*.py` (only when `DEVOS_ENABLE_LOCAL_PLUGINS=1`). Loading is
fail-safe (`LOADED`/`ERRORS`); `devos plugins` reports state. Loading executes third-party code —
a deliberate, documented trust boundary (SECURITY §5/§8). See DECISIONS.md D-0016.

### Career Assistant (`modules/career` + `job_leads`, Phase 9 slice 4)
Job leads live in the `job_leads` table (schema v4) with CRUD in `storage/repo` mirroring tasks
(`devos job`). `career.analyze_cv` is deterministic/offline keyword overlap (reuses `qa.question_terms`)
between a local CV file and a job's notes (`devos cv`). `career.interview_prep` reuses the provider
seam, grounded only on a job's stored notes, declining when noteless (`devos interview`). Local-first,
read-only except job CRUD; no scraping/APIs. See DECISIONS.md D-0015.

### Learning Assistant (`modules/learning`, Phase 9 slice 1)
`learning.learn(conn, target, *, provider, level, project, limit) -> Lesson` gives a grounded,
leveled (eli5/intermediate/advanced) explanation: **file mode** grounds on an indexed file's
chunks (via `repo.find_project_for_path`/`find_file_by_path`/`get_file_chunks`), **topic mode**
via `qa.retrieve`; declines (no provider call) when ungrounded. Same compose-existing-layers
pattern as `debug`/`docgen` — no new retrieval logic or schema. `learn` (explain), `quiz` (review
questions), `exercise` (practice tasks), and `grade` (evaluate a learner's answer vs the code →
feedback/strengths/weaknesses) all share `_resolve_chunks` + assemble + provider; commands print
via the shared `ask_cmd.print_answer`. All read-only/stateless, decline when ungrounded. Phase 9 is
built as separately-approved slices. See DECISIONS.md D-0012/D-0013/D-0014.

### Documentation Automation (`modules/docgen`, Phase 8)
`docgen.generate(conn, doc_type, *, provider, project, limit)` reuses the Q&A pipeline:
code docs (readme/architecture/api/setup) ground on `qa.retrieve` + project facts; record
docs (changelog/decisions/milestone) ground on `repo.list_memory`/`list_tasks` (including
global records). One `provider.complete()` call → `GeneratedDoc`; declines (no provider call)
when ungrounded. `devos docgen` prints to stdout by default and writes to `--output` only
(no overwrite without `--force`); attribution is retrieval/record-derived. See DECISIONS.md D-0011.

### Dashboard & local API (`devos/api`, Phase 7)
`devos/api/app.py` holds read-only **data builders** (`overview`/`projects`/`tasks`/`memory`/`recall`
payloads) that reuse `storage/repo` + `modules.recall`, plus a socket-free `route(ws, path, query)
-> Response` table (JSON `/api/*`; static files under `static/`, path-traversal-rejected).
`devos/api/server.py` wraps `route()` in a stdlib `ThreadingHTTPServer` **bound to 127.0.0.1 only**,
opening a per-request connection. The frontend (`static/index.html` + `app.js`) is a **React + htm**
SPA (no build step) with React/ReactDOM/htm **vendored locally** for offline use. `devos serve` runs
it. Read-only this phase; future write endpoints route through the safe-action model with a
token/CSRF (SECURITY §8). See DECISIONS.md D-0010.

### Debug Assistant (`modules/trace` + `modules/debug`)
`modules/trace` is pure, pluggable trace/log parsing (Python/Node/generic; register a parser
in `TRACE_PARSERS` to add a language) → `ParsedTrace(error_type, error_message, frames)`.
`modules/debug.diagnose` orchestrates: parse → **locate frames in the index only**
(`repo.find_file_by_path`; never opens trace-named filesystem paths) → **reuse** `qa.retrieve`
+ `qa.assemble_context` → generate via `providers/ai`. Output (`DebugDiagnosis`) separates
deterministic evidence (error, located `file:line`, sources) from the provider's analysis and
carries a confidence heuristic; it declines (no provider call) when no evidence is found.
See DECISIONS.md D-0008 and SECURITY.md §5.

## Configuration & data location
- Data dir resolution order: `DEVOS_HOME` env var → `%APPDATA%\DeveloperOS` (Windows)
  / `~/.local/share/devos` (POSIX). Created on `devos init`.
- A project-local marker (`.devos/`) may be added in Phase 2 to bind a folder to a project.

## Provider abstraction (AI)
`providers/ai.py` defines `AIProvider` with methods like `complete(prompt, *, system, context)`
returning a structured result. `MockAIProvider` returns deterministic, clearly-labeled
stub output (echoing assembled context) so the full pipeline is testable offline. A
`get_provider()` factory selects implementation from config/env; a real Claude provider
is added later without touching callers.

## Interfaces
- **CLI (now):** `argparse` dispatcher in `cli.py`; each command in `commands/` registers
  a name, args, and handler. Output is plain text now; Rich/Typer considered in Phase 7.
- **Local API + React dashboard (Phase 7):** reads the same SQLite/services layer.

## Safety model
- Read/inspect operations run freely. **Mutating** operations (file edits, git
  commits/branches, installs, builds) are performed by the **Safe Action Agent** with
  explicit confirmation and a clear description of changes. No silent destructive actions.

## Testing
- `tests/` uses stdlib `unittest` (runs via `python -m unittest` with zero external
  deps; also discoverable by pytest later). Each phase adds tests as part of its
  Definition of Done.
