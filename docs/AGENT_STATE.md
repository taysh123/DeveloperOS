# AGENT_STATE — Single Source of Truth

> Read this FIRST every session. It is the authoritative record of where the project
> stands and what to do next. Update it after every meaningful work session.

_Last updated: 2026-06-01_

## Current phase
**Phase 3 — Code Indexing & Search** (Phases 0–2 complete).

## Current milestone
Build a searchable index: chunk indexed files, populate the `chunks` + `chunks_fts`
(FTS5) tables, and add `devos index` + `devos search <query>` (keyword), with a design
seam for embeddings/semantic search later.

## Next immediate step
Start Phase 3 test-first: add a `modules/index` service that reads each recorded file,
splits it into line-ranged chunks, stores them in `chunks`, and mirrors content into
`chunks_fts`. Implement incremental reindex keyed on `files.content_hash`. Wire up
`devos index` and `devos search`. Write the chunking/search tests first.

## Tasks
### In progress
- _None (Phase 2 just completed; Phase 3 not yet started)._

### Completed
- [x] Phase 0: vision confirmed; 4 foundational decisions made (see DECISIONS.md).
- [x] Created/populated mandatory docs: PROJECT_BRIEF, ROADMAP, ARCHITECTURE, AGENT_STATE,
      TODO, PROGRESS_LOG, DECISIONS, CHANGELOG, KNOWN_ISSUES.
- [x] Phase 1: scaffolded `devos` package (cli, config, storage+schema, providers/ai mock,
      commands, core/workspace, module stubs); `pyproject.toml`, `.gitignore`, `README.md`.
- [x] Phase 1: `pip install -e .` works; `devos --version|init|status` verified end-to-end;
      10 smoke tests pass (`python -m unittest`); first git commit made.
- [x] Phase 2: ingestion — `modules/ingest` (walk + ignore rules + .gitignore subset +
      binary/size skip + heuristic classification) and `storage/repo` (idempotent upserts);
      `devos scan` + `devos projects`. 15 new tests (25 total) pass; dogfooded on this repo
      (35 files classified, idempotent rescan, no duplicate project).

### Blocked
- _None._

## Known assumptions
- Single power user; multi-user is a future extension.
- Foundation runtime is stdlib-only (no external pip deps required to run).
- AI is mocked until a real Claude provider is wired in (no API key needed yet).
- Windows is the primary dev OS (paths handled cross-platform via `pathlib`).

## Open decisions
- CLI framework: stdlib `argparse` now; revisit Typer/Rich in Phase 7. _(Default chosen.)_
- Embeddings/semantic search backend: deferred to Phase 3+. _(Open.)_

## Working context
- Repo: `C:\Projects\DeveloperOS` · git branch: `main` · platform: Windows 11 · Python 3.13.5.
- No remote configured yet.
- Run app: `pip install -e .` then `devos <command>`. Tests: `python -m unittest discover -s tests`.
- Isolate the data dir in dev/tests via the `DEVOS_HOME` env var.

## How to continue (session startup)
1. Read this file. 2. Read ROADMAP.md. 3. Read TODO.md. 4. Read latest PROGRESS_LOG.md entry.
5. Read DECISIONS.md / KNOWN_ISSUES.md if relevant. 6. Resume from "Next immediate step".
