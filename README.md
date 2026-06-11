# DeveloperOS

**Your private, local-first workspace for understanding, organizing, and learning from your own code — everything stays on your machine.**

[![CI](https://github.com/taysh123/DeveloperOS/actions/workflows/ci.yml/badge.svg)](https://github.com/taysh123/DeveloperOS/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/taysh123/DeveloperOS)](https://github.com/taysh123/DeveloperOS/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## What is DeveloperOS?

DeveloperOS is a **personal operating system for developers**: point it at your project folders and it builds a private, searchable index you can **search, question, study, and work from** — in a real **desktop app window**, through a friendly local dashboard, or from a full CLI.

- **Understand any project**: plain-English Q&A and file explanations grounded in your real code, always cited as `file:line` — it declines instead of guessing.
- **Study mode**: a per-project Deep Dive (key files, how it works, study questions, interview prep).
- **Learning center**: leveled explanations, quizzes, exercises, and answer grading from your own codebase.
- **Career tools**: job-lead tracking, offline CV keyword matching, grounded interview prep.
- **Meeting summaries**: paste notes/transcripts → summary, decisions, and action items that become tasks in one click.
- **Search & Ask, Debug assistant, tasks, notes, and doc generation** — one coherent system.
- **AI on your terms**: an offline mock provider by default, optional free local AI via Ollama, and a provider architecture ready for more. No API key is ever required.
- **Offline-first philosophy**: no account, no cloud, no telemetry. The dashboard binds to `127.0.0.1` only.

## Key features

| Group | Features |
|---|---|
| **Understand** | Project import & incremental indexing (SQLite FTS5) · ranked code search · grounded **Ask** with `file:line` citations · file/project **Explain** · **Debug assistant** (paste a stack trace → evidence, root cause, fix — file lookups are index-only) · **Project Deep Dive / Study** |
| **Learn** | Leveled code explanations (ELI5 → advanced) · grounded quizzes · practice exercises · answer **grading** with strengths/weaknesses |
| **Build** | Tasks (status/priority/projects, inline edit) · notes & long-term memory · **recall** across memory+tasks+code · **meeting summaries → tasks** · grounded doc generation (`devos docgen`) |
| **Grow** | Job-lead tracking · **CV match check** (offline keyword coverage; CV text never stored) · interview prep grounded in your notes · onboarding **get-started guide** |
| **System** | Settings & AI management (provider catalog, key-presence-only display) · plugin seam (`devos plugins`) · **standalone desktop window** + launcher + Windows installer + installable PWA · CSRF-guarded loopback API · secret-aware scanning |

## Screenshots

*Placeholder — screenshots to be added. Planned shots: Dashboard Home (welcome guide + overview), Project Deep Dive, Learning Center, Career Center, Meeting Summary, Settings & AI management, and the Windows installer / Start-Menu launch experience. Run `devos app` to see all of it live in the meantime.*

## Quick start

**Easiest (Windows, no Python needed):** grab the installer from the
[**latest release**](https://github.com/taysh123/DeveloperOS/releases) —
`DeveloperOS-Setup-<version>.exe` installs per-user (no admin rights), adds a Start-Menu
shortcut, and uninstalls cleanly without touching your data. A portable `DeveloperOS.exe`
(no install) is attached too. The binaries are unsigned, so SmartScreen may ask for
confirmation on first run (More info → Run anyway).

**From source (any platform, Python ≥ 3.11, zero runtime dependencies):**
```bash
pip install -e .

devos app          # opens DeveloperOS in its own desktop window (recommended)
```

The first run creates your private workspace automatically and the dashboard's welcome
guide walks you through importing a project, searching, and asking your first question.

**CLI essentials:**
```bash
devos init                   # create the local data dir + SQLite database
devos scan <path>            # import a project folder
devos index <path>           # scan + build the searchable index
devos search "auth flow"     # ranked keyword search with file:line
devos ask "how does login work?"   # grounded Q&A with citations
devos serve                  # dashboard only (no auto-open); devos --help for everything
```

**Development:**
```bash
python -m unittest discover -s tests     # full suite (stdlib only, no test deps)
```

**Build the desktop artifacts (Windows, dev-time tools only):**
```powershell
cd packaging
./build.ps1               # PyInstaller -> dist/DeveloperOS.exe
./build_installer.ps1     # Inno Setup  -> dist/DeveloperOS-Setup-<version>.exe
```

## Desktop experience

The full desktop ladder is shipped (decisions D-0029–D-0033):

- **A real app window** — launching DeveloperOS opens a **standalone desktop window** (no browser chrome, no address bar, its own taskbar entry), using the app mode of Edge/Chrome already on your machine — zero extra runtime. Falls back to your default browser if needed; `devos app --browser` gives a plain tab on purpose.
- **`DeveloperOS.exe`** — single-file executable; no Python required. Double-click → window opens.
- **Windows installer** — per-user setup (no admin rights) with a Start-Menu shortcut and a clean uninstall that **preserves your data** (`%APPDATA%\DeveloperOS`).
- **`devos app` launcher** — starts (or reuses — never duplicates) the local backend, waits for readiness, opens the window; Ctrl+C in its console stops everything.
- **Installable PWA** — alternatively, open the dashboard in Edge/Chrome and click *Install* (no service worker; nothing changes about the local backend).
- **Updates are manual by design**: check the [Releases](https://github.com/taysh123/DeveloperOS/releases) page; a newer Setup upgrades in place. No auto-updater, no phoning home.

Electron was evaluated and rejected (size, toolchain, surface); Tauri stays parked unless tray/dialog-level OS integration ever becomes a real need — the app-mode window achieves the goal with zero added weight.

## Architecture

```
User (browser / installed PWA / DeveloperOS.exe / CLI)
        │
        ▼
Dashboard — React + htm SPA, vendored offline (no build step, no CDN)
        │
        ▼
API layer — stdlib http.server on 127.0.0.1 only
            CSRF token + Origin allowlist + JSON-only + size caps on every write
        │
        ▼
Core modules — qa · debug · learning · career · meeting · recall · docgen · ingest/index
               (+ provider seam: mock | Ollama | future)
        │
        ▼
Project index — local SQLite + FTS5 (your code, tasks, notes, memory; incremental, content-hashed)
```

- **Dashboard**: one SPA, ten tabs, full parity with the CLI; design tokens + WAI-ARIA accessibility.
- **API layer**: loopback-only; read endpoints are read-only, writes are guarded; no CORS is ever emitted.
- **Core modules**: every AI surface retrieves first and answers grounded with citations, or declines.
- **Index**: everything lives in one local SQLite database under your user profile; deleting a project from DeveloperOS never touches files on disk.

More: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · decision log in [`docs/DECISIONS.md`](docs/DECISIONS.md).

## AI philosophy

- **AI is opt-in and mocked by default.** Out of the box, AI surfaces return clearly-labeled offline stub output — retrieval, grounding, and citations are fully real.
- **No API key, ever required.** DeveloperOS never requires a paid API and never falls back to a cloud service.
- **Free local AI via [Ollama](https://ollama.com)** (optional): `ollama pull llama3.2`, then pick **Ollama** in Settings → AI provider (or `DEVOS_AI_PROVIDER=ollama`). Configure with `DEVOS_OLLAMA_URL` / `DEVOS_OLLAMA_MODEL`. If Ollama isn't running, DeveloperOS says so plainly and keeps working.
- **Provider architecture**: AI runs behind a small `AIProvider` seam; cloud providers (Claude/OpenAI) are catalogued in Settings but deliberately unwired under the project's no-cost policy — selecting one keeps the offline mock effective.
- **You stay in control**: a global AI on/off toggle always wins, and the Settings tab shows only whether a key is *present* in your environment — key values are never stored or displayed.

## Privacy & security

- **Local-first**: all data (index, tasks, notes, settings) lives in a single SQLite database under your user profile, git-ignored, never uploaded.
- **Offline-first**: no account, no telemetry, no background network activity. The only optional network hop is to an Ollama daemon **on your own machine**.
- **Secret-aware indexing**: credential-looking files (`.env*`, key files, keystores, `credentials*`, …) are skipped *before a single byte is read* — secrets can't reach the index.
- **Guarded writes**: every state-changing endpoint requires a per-session CSRF token plus an Origin allowlist; the server binds to `127.0.0.1` only.
- **Honest grounding**: AI answers cite `file:line` computed by the retrieval layer (not the model) and decline when context is insufficient.

Full security model: [`docs/SECURITY.md`](docs/SECURITY.md).

## Current status

| | |
|---|---|
| **Version** | v0.8.0 — "DeveloperOS as a desktop product" (native app window already on `main`) |
| **Milestone** | Roadmap phases 0–9 complete · dashboard slices 1–16 shipped · **desktop ladder complete** (PWA → launcher → exe → installer → app window) |
| **Tests** | 361 (stdlib unittest, TDD) |
| **CI** | GitHub Actions — Python 3.11/3.12/3.13 × Linux + Windows on every push/PR |
| **Platforms** | Windows-first (installer/exe); dashboard & CLI run anywhere Python ≥ 3.11 does |

## Roadmap

- **Done**: CLI foundation (scan/index/search/ask/explain/debug/tasks/memory/docgen/learning/career/plugins/meeting) → full-parity dashboard in 11 slices → design system + accessibility → onboarding → first real AI provider (Ollama) → CI → PWA → launcher → `DeveloperOS.exe` → Windows installer → **standalone app window**.
- **Current**: desktop ladder complete; next release (v0.9.0) pending.
- **Upcoming**: Plugins/Extensions UI · semantic search behind the prepared embeddings seam · real screenshots · cloud AI providers only if the no-cost policy ever changes.

Live state: [`docs/AGENT_STATE.md`](docs/AGENT_STATE.md) · plan: [`docs/ROADMAP.md`](docs/ROADMAP.md) + [`docs/FUTURE_ROADMAP.md`](docs/FUTURE_ROADMAP.md).

## Contributing

The repo is docs-driven and TDD-built — a good place to start:

1. Read [`docs/AGENT_STATE.md`](docs/AGENT_STATE.md) (single source of truth) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
2. `pip install -e .` then `python -m unittest discover -s tests` — the suite is stdlib-only and fast.
3. Branch → tests first → implementation → docs sync (`CHANGELOG`, `AGENT_STATE`, friends) → PR. CI must be green.
4. Keep the constraints: stdlib-only runtime, offline by default, no paid APIs, security posture intact.

## License

[MIT](LICENSE).
