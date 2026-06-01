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

More commands (`scan`, `search`, `ask`, `debug`, `task`, …) arrive per the
[roadmap](docs/ROADMAP.md).

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
