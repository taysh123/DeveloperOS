# DeveloperOS

**An AI-powered personal operating system for developers.** One coherent system to
understand any project deeply, debug it, track work, remember decisions, search across
everything, and generate docs — built for a single power user first.

> Status: **early foundation (Phase 1)**. CLI-first, local-first, stdlib-only runtime.
> See [`docs/`](docs/) for the full vision, roadmap, architecture, and live state.

## Quick start
```bash
# from the repo root
pip install -e .

devos --version
devos init       # create the local data dir + SQLite database
devos status     # show where DeveloperOS stands
```

No API key or network is required for the foundation: AI features run against a built-in
**mock provider** until a real Claude provider is wired in (Phase 4+).

## Commands (current)
| Command | Description |
|---|---|
| `devos init` | Create the local data directory and initialize the SQLite database. |
| `devos status` | Report data location, schema version, provider, and stored counts. |
| `devos scan <path>` | Scan a project folder and record/refresh its file inventory (classified, idempotent). |
| `devos projects` | List registered projects with file counts and last-scanned time. |
| `devos index <path>` | Scan then build/refresh the searchable index (chunks + FTS5, incremental). |
| `devos search <query>` | Ranked keyword search with `file:line` references and snippets (`--project`, `--limit`). |
| `devos ask "<question>"` | Grounded Q&A over indexed code; cites `file:line` sources, declines instead of guessing. |
| `devos explain [path]` | Explain a file (from its chunks) or a whole-project overview, with citations. |
| `devos debug [trace]` | Diagnose an error/stack trace/log (arg, `--file`, or piped stdin): evidence, root cause, fix, verification, with `file:line` sources. |
| `devos task <add\|list\|show\|set\|rm>` | Track tasks/bugs/features with status, priority, kind, milestone, and notes. |
| `devos remember <title>` | Store a long-term memory (decision/summary/preference/note) with tags. |
| `devos recall <query>` | Search across memory, tasks, and indexed code in one place (offline). |
| `devos serve` | Launch the local **dashboard** (read-only, 127.0.0.1) — overview, task status, blocked, recent activity, "where I left off", recall. |
| `devos docgen <type>` | Generate grounded docs (readme/architecture/api/setup/changelog/decisions/milestone); stdout or `--output` (no overwrite without `--force`). |
| `devos learn <path\|topic>` | Learn your code at a chosen depth (`--level eli5\|intermediate\|advanced`), grounded with `file:line` sources. |
| `devos quiz <path\|topic>` | Generate grounded review questions (`--n N`) about a file or topic, with `file:line` sources. |
| `devos exercise <path\|topic>` | Generate grounded practice exercises (`--n N`) about a file or topic. |
| `devos grade <path\|topic>` | Evaluate your answer (`--answer`/`--answer-file`) against the code: feedback + strengths/weaknesses + sources. |
| `devos job <add\|list\|show\|set\|rm>` | Track job leads (company, role, status, notes). |
| `devos cv <file> [--job ID]` | Keyword-match a local CV against job notes (offline): matched/missing + coverage. |
| `devos interview <job-id>` | Interview-prep questions grounded in a job lead's notes. |

AI answers use an offline **mock** provider by default (no API key); see [`docs/SECURITY.md`](docs/SECURITY.md).
The dashboard is a React (htm) SPA vendored locally — no build/npm, fully offline.

## How it's built
- **Python core + CLI** now; a **TypeScript/React dashboard** comes in Phase 7.
- **Local-first SQLite** storage with FTS5 keyword search (semantic search later).
- **Provider abstraction** for AI, so models are swappable.
- **Stdlib-only runtime** for the foundation, so it runs anywhere.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the design and
[`docs/AGENT_STATE.md`](docs/AGENT_STATE.md) for the current source-of-truth state.

## Development
```bash
python -m unittest discover -s tests -v   # run the test suite (stdlib, no deps)
```

## License
MIT.
