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
- `devos debug`: turn an error / stack trace / log (argument, `--file`, or piped stdin) into a grounded, structured diagnosis. Parses Python/Node/generic traces, locates the referenced files/lines **in your index**, retrieves related code, and asks the AI provider for Observed evidence / Likely root cause / Assumptions / Recommended fix / Verification steps — with `file:line` citations and an explicit confidence level. Declines instead of guessing when there's no evidence. Trace-named filesystem paths are never read (index-only lookups).
- `devos task` (add / list / show / set / rm): track tasks, bugs, and features with status (todo/in_progress/blocked/done), priority (low/medium/high), kind, milestone, and notes — optionally scoped to a project.
- `devos remember`: store long-term memory entries (decision / summary / preference / note) with tags; duplicate entries are de-duplicated.
- `devos recall`: search across your memory, tasks, and indexed code in one command (offline, with `file:line` for code). Storage upgraded to schema v3 (`tasks.priority`).
- `devos serve`: a local **dashboard** web UI (read-only, bound to 127.0.0.1) over the existing data — project overview, task status board, blocked items, recent activity, "where I left off", and a recall search box. Built on a stdlib `http.server` JSON API with a React (htm) front-end **vendored locally** (no build step, no npm, fully offline).
- `devos learn <path|topic> [--level eli5|intermediate|advanced]`: a learning assistant that explains your indexed code at the chosen depth, grounded in real source with `file:line` citations. Pass a file to explain that file, or a topic to retrieve relevant code. Declines instead of guessing when nothing relevant is indexed. Offline, mock provider by default.
- `devos quiz <path|topic> [--n N]`: generate N grounded review questions about a file or topic from your indexed code (default 5), with `file:line` sources. Declines instead of guessing when nothing relevant is indexed. Offline, mock provider by default.
- `devos plugins` + a plugin/extension system: external packages (entry-point group `devos.plugins`) and opt-in local files (`<data-dir>/plugins/*.py`, enabled with `DEVOS_ENABLE_LOCAL_PLUGINS=1`) can register new commands and AI providers. Plugin failures are isolated and listed by `devos plugins`. (Loading plugins runs third-party code — see SECURITY.md.)
- `devos job <add|list|show|set|rm>`: track job leads with company, role, url, status (saved/applied/interview/offer/rejected/closed), and notes.
- `devos cv <file> [--job ID]`: analyze a local CV/resume against a job's notes (or all tracked jobs) — offline keyword matching with matched/missing keywords and a coverage figure. No AI, fully local.
- `devos interview <job-id> [--n N]`: generate interview-prep questions grounded in a job lead's notes, citing the job as source. Declines when the job has no notes.
- `devos exercise <path|topic> [--n N]`: generate N grounded, hands-on practice exercises from your indexed code (default 3), with `file:line` sources.
- `devos grade <path|topic> --answer <text>|--answer-file <f> [--question <q>]`: evaluate your answer against the actual code — feedback with Strengths and Weaknesses, plus `file:line` sources. Read-only; declines when nothing relevant is indexed. Offline, mock provider by default.
- `devos docgen <type>`: generate grounded documentation — `readme`, `architecture`, `api`, `setup` (from indexed code + project facts) and `changelog`, `decisions`, `milestone` (from your memory/tasks). Prints to stdout by default; `--output PATH` writes a file (never overwrites without `--force`); appends a Sources footer (`file:line` for code, titles for records). Declines instead of guessing when there's nothing to ground on. Offline, mock provider by default.
