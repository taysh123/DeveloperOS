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
