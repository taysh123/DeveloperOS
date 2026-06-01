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
- **files** — `id, project_id, rel_path, lang, category, size, content_hash, indexed_at`
  (category ∈ frontend/backend/db/api/auth/test/config/other; filled in Phase 2).
- **chunks** — `id, file_id, start_line, end_line, tags, content_hash` (Phase 3).
- **chunks_fts** — FTS5 virtual table over chunk/file content for keyword search (Phase 3).
- **tasks** — `id, project_id, title, kind(task|bug|feature), status, milestone, notes, created_at, updated_at` (Phase 6).
- **memory** — `id, project_id, kind, title, body, tags, created_at` (Phase 6).
- **schema_migrations** — applied migration versions (foundation).

A lightweight versioned migration runner applies `schema.sql` / numbered migrations
idempotently; re-running is safe.

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
