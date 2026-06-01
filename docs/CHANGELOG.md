# DeveloperOS — Changelog

All notable, user-visible changes. Format loosely follows Keep a Changelog.

## [Unreleased]
### Added
- Project foundation: vision brief, phased roadmap (0–9), architecture, and source-of-truth state files.
- `devos` CLI with `init` (creates local data dir + SQLite DB, schema v1) and `status` (reports location, schema, provider, stored counts).
- Local-first SQLite storage layer with idempotent schema/migrations and an FTS5 search table reserved for indexing.
- AI provider abstraction with a built-in offline mock provider (no API key required).
- Editable install via `pip install -e .` exposing the `devos` command; 10 stdlib smoke tests.
- `devos scan <path>`: ingest a project folder — walks files with sensible ignore rules (a `.gitignore` subset, `node_modules`/venvs/build dirs, binary & oversized files), classifies each file into frontend/backend/db/api/auth/test/config/other, and records an idempotent file inventory (added/updated/unchanged/removed/skipped summary + per-type breakdown).
- `devos projects`: list registered projects with file counts and last-scanned time.
- `devos index <path>`: scan then build/refresh a searchable index — splits files into line-ranged chunks, mirrors them into a SQLite FTS5 index, and reindexes incrementally (only changed files, via content hash). Reports (re)indexed/unchanged/skipped files and chunk counts.
- `devos search <query>`: ranked keyword search (bm25) across indexed code/docs, returning `file:line-range` locations with highlighted snippets; supports `--project` and `--limit`.
- Storage upgraded to schema v2 (`files.indexed_hash`) with an upgrade-capable migration runner.
- `devos ask "<question>"`: grounded Q&A over your indexed project(s). Retrieves relevant chunks, answers via the configured AI provider (offline mock by default — no API key), and cites `file:line` sources. Clearly declines instead of guessing when there isn't enough indexed context.
- `devos explain [path]`: plain-language explanation of a specific file (from its indexed chunks) or a whole-project overview (file-type breakdown + notable files), with source citations.
- Added `docs/SECURITY.md` documenting the security-by-design architecture future phases must respect.
