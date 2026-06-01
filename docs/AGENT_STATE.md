# AGENT_STATE — Single Source of Truth

> Read this FIRST every session. It is the authoritative record of where the project
> stands and what to do next. Update it after every meaningful work session.

_Last updated: 2026-06-01_

## Current phase
**Phase 5 — Debug Assistant** is NEXT (Phases 0–4 complete). _Not started._

## Current milestone
(Upcoming, do not start without going through planning.) Parse errors/stack traces/logs,
locate referenced files/lines, assemble context (reuse `modules/qa` retrieval), and propose
cause/fix/verification via the provider — `devos debug`. No silent file writes.

## Next immediate step
Begin Phase 5 by re-running the session-startup procedure and `/plan`. Phase 5 will reuse
`modules/qa` (retrieval + grounded answers) and `providers/ai`; likely add per-language
trace parsers. The mock provider stays default (no API keys).

## Tasks
### In progress
- _None (Phase 4 just completed; Phase 5 not yet started)._

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
- [x] Phase 3: indexing & search — schema v2 + upgrade-capable migration runner; `modules/index`
      (line-window `chunk_text`, incremental `index_project` keyed on `files.indexed_hash`,
      bm25 `search` returning `SearchHit`, safe FTS query builder); `storage/repo` chunk/search
      helpers + `reconcile_fts`; `devos index` + `devos search`. 20 new tests (45 total) pass;
      dogfooded on this repo (40 files → 90 chunks; 2nd index 0 re-indexed/40 unchanged; ranked
      located snippets). Architecture decision D-0006 logged (semantic-search seam).
- [x] Phase 4: Q&A & understanding — `modules/qa` (OR-retrieval + stopwords, context assembly,
      grounded `answer` that declines without calling the provider when retrieval is empty,
      `explain` for files + project overview); `index.search`/`build_match_query` gained an `op`
      param; `repo` retrieval helpers; `devos ask` + `devos explain` (cite file:line). Uses the
      MockAIProvider via `ws.ai` (no keys). 21 new tests (66 total) pass; dogfooded on this repo
      (grounded answers w/ sources; decline path verified). Added `docs/SECURITY.md` and D-0007.

### Blocked
- _None._

## Known assumptions
- Single power user; multi-user is a future extension.
- Foundation runtime is stdlib-only (no external pip deps required to run).
- AI is mocked until a real Claude provider is wired in (no API key needed yet).
- Windows is the primary dev OS (paths handled cross-platform via `pathlib`).

## Open decisions
- CLI framework: stdlib `argparse` now; revisit Typer/Rich in Phase 7. _(Default chosen.)_
- Semantic-search *architecture* decided (D-0006: `SearchHit` seam + per-chunk hash). The
  embeddings *backend* (which local model/library) remains open and deferred to a later phase.

## Working context
- Repo: `C:\Projects\DeveloperOS` · git branch: `main` · platform: Windows 11 · Python 3.13.5.
- No remote configured yet.
- Run app: `pip install -e .` then `devos <command>`. Tests: `python -m unittest discover -s tests`.
- Isolate the data dir in dev/tests via the `DEVOS_HOME` env var.

## How to continue (session startup)
1. Read this file. 2. Read ROADMAP.md. 3. Read TODO.md. 4. Read latest PROGRESS_LOG.md entry.
5. Read DECISIONS.md / KNOWN_ISSUES.md if relevant. 6. Resume from "Next immediate step".
