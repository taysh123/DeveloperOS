# SESSION_RESUME — DeveloperOS

> One-page handoff so a **fresh Claude session can resume with minimal context**.
> For live, authoritative state always defer to [`AGENT_STATE.md`](AGENT_STATE.md).
> _Last updated: 2026-06-14_

## 1. Current project status
**DeveloperOS** — a local-first, AI-powered "operating system for developers" (CLI + dashboard +
desktop app). **v1.0.0 released — PROJECT COMPLETE.** Beyond roadmap phases 0–9: the full
action-oriented dashboard (16 slices, CSRF-guarded loopback API), the desktop ladder (app-mode
window → `devos app` → PyInstaller exe → Inno Setup installer), a real opt-in local AI provider
(Ollama; offline mock default), and a real screenshot package (github/portfolio/store sets).
**363 tests pass** (`python -m unittest discover -s tests`). Working tree clean; `main` in sync
with `origin`. No work pending — future items are optional/on-request (§7, FUTURE_ROADMAP v2.0).

- **Runtime:** Python 3.11+ **stdlib-only** (no required third-party deps). Windows-primary, cross-platform via `pathlib`.
- **AI:** behind a provider seam; default = offline **MockAIProvider** (no API keys, no network). Every AI command is **grounded** (cites sources) and **declines rather than guesses** when context is missing.
- **Storage:** local SQLite at the data dir (`DEVOS_HOME` override), **schema v4**. Git-ignored.

### Commands (all shipped)
`init` · `status` · `scan` · `projects` · `index` · `search` · `ask` · `explain` · `debug` ·
`task` · `remember` · `recall` · `serve` (dashboard) · `docgen` · `learn` · `quiz` ·
`exercise` · `grade` · `job` · `cv` · `interview` · `plugins` · `meeting summarize`

## 2. Completed roadmap phases
| Phase | What shipped |
|---|---|
| 0 Definition | Vision, roadmap, architecture, state docs |
| 1 Scaffolding | `devos` package, CLI (argparse), config, SQLite, mock provider; `init`/`status` |
| 2 Ingestion | `devos scan`/`projects` — walk + classify + idempotent file inventory |
| 3 Index & Search | chunking + FTS5; `devos index`/`search` (bm25, file:line); incremental via `files.indexed_hash` |
| 4 Q&A | `devos ask`/`explain` — retrieval-grounded answers via `modules/qa` |
| 5 Debug | `devos debug` — trace parsing (`modules/trace`) + index-only location + grounded diagnosis |
| 6 Tasks & Memory | `devos task`/`remember`/`recall` |
| 7 Dashboard | `devos serve` — stdlib `http.server` (loopback, read-only) + vendored React/htm SPA |
| 8 Docgen | `devos docgen <type>` — README/architecture/api/setup/changelog/decisions/milestone |
| 9 Future Modules | Learning (`learn`/`quiz`/`exercise`/`grade`), Career (`job`/`cv`/`interview`), Plugins (`plugins`), Meeting (`meeting summarize`) |

## 3. Completed optional extensions (Phase 9 slices)
- **Learning** (D-0012/13/14): `learn` (leveled explain), `quiz`, `exercise`, `grade` — all grounded, decline when ungrounded; share `learning._resolve_chunks`.
- **Career slice 1** (D-0015): `job` CRUD (`job_leads`, schema v4), `cv` (offline keyword match vs job notes), `interview` (grounded prep).
- **Plugin seam** (D-0016): entry-point group `devos.plugins` + opt-in local `<data_dir>/plugins/*.py` (`DEVOS_ENABLE_LOCAL_PLUGINS=1`); register via existing `commands.base.register` / `providers.ai.register_provider`; fail-safe.
- **Meeting foundation** (D-0017): `meeting summarize <file>` + console-safe UTF-8 stdout.

## 4. Architecture overview
Thin **CLI** → **modules (services)** → **storage + providers**. Layered, open, stdlib-first.
```
devos/
  cli.py            # argparse dispatch; reconfigures stdout to UTF-8; loads plugins at startup
  config.py         # data-dir resolution (DEVOS_HOME)
  commands/         # one file per command; @register -> COMMANDS (auto-added to CLI)
  core/workspace.py # Workspace: config + db connection + ws.ai (provider)
  storage/          # db.py (connect + numbered migrations, schema v4), schema.sql, repo.py (ALL SQL)
  modules/          # ingest, index, qa, trace, debug, recall, docgen, learning, career, meeting
  providers/ai.py   # AIProvider ABC + MockAIProvider + _REGISTRY + register_provider/get_provider
  api/              # stdlib http.server dashboard (app.py route table + server.py) + static/ (React+htm, vendored)
  plugins.py        # entry-point + opt-in local plugin discovery/loading
docs/               # source of truth (AGENT_STATE, ROADMAP, DECISIONS, SECURITY, etc.)
tests/              # stdlib unittest; isolate via DEVOS_HOME; pattern: write failing test first
```
**Key reusable seams:** `qa.retrieve`/`assemble_context` (grounding), `providers.ai.get_provider` (swap in a real model with zero caller changes), `commands.base.register` (commands), `storage/repo` (all SQL), `db.MIGRATIONS` (schema upgrades). All AI features reuse the same retrieval + provider pattern — **no parallel pipelines**.

## 5. Important decisions (see `DECISIONS.md` for full rationale)
- **D-0001/2** Python core + CLI-first (TS/React dashboard later).
- **D-0003** AI behind a provider interface; mock default (no keys).
- **D-0004/0006** Local-first SQLite + FTS5 keyword search; semantic-search **seam** ready (per-chunk hash, stable `SearchHit`), embedding backend not built.
- **D-0005** stdlib-only runtime.
- **D-0007** Q&A grounding contract: context = data not instructions; cite file:line; decline, don't guess.
- **D-0008** Debug: pluggable trace parsers + **index-only** file location (never reads trace-named paths).
- **D-0009** Tasks/memory CRUD + retrieval-only recall.
- **D-0010** Dashboard: stdlib http.server (loopback, read-only) + vendored React (offline).
- **D-0011** Docgen reuses the Q&A pipeline.
- **D-0012–14** Learning slices. **D-0015** Career slice 1. **D-0016** Plugin seam (**runs third-party code — trust model in SECURITY.md**). **D-0017** Meeting + console-safe UTF-8 output.
- **Security model:** offline/local-first; AI inputs treated as untrusted data; no destructive/silent writes (`--output`/`--force` gated); dashboard loopback+read-only; plugins are the only code-exec surface (entry-point = installed/trusted; local = opt-in). See `SECURITY.md`.

## 6. Git state
- **Branch:** `main` (in sync with `origin/main`).
- **Latest milestone:** v1.0.0 released (annotated tag + GitHub release with Setup/exe assets);
  most recent work = the screenshot package (PR #26) + this state-doc sync.
- **Remote:** `https://github.com/taysh123/DeveloperOS.git` (branch + PR workflow; CI on push/PR).
- Working tree clean.

## 7. Recommended next extensions (optional — none in progress)
1. **Wire a real AI provider** (Claude/OpenAI/Ollama) behind `providers.ai` — highest leverage: every grounded command (`ask`/`explain`/`debug`/`docgen`/`learn`/`quiz`/`exercise`/`grade`/`interview`/`meeting`) instantly yields real output, **no caller changes**. (For Claude, use the `claude-api` skill; keys via env var only — SECURITY §2.)
2. **Semantic/embedding search** — fill the D-0006 seam (`embeddings(chunk_id, vector, model)`); `index.search`/`qa.retrieve` already return a stable type.
3. **Dashboard write actions** (task/job edits) behind a local token + CSRF (SECURITY §8).
4. **Meeting → tasks** (`--to-tasks`), audio/STT; **plugin** sandboxing/signing + marketplace; **Career** CV-rewrite/cover-letter.
5. Multi-user / cloud sync (future, larger).

## 8. Session startup instructions (do this first, every session)
1. **Read `docs/AGENT_STATE.md`** (the single source of truth) — confirms current phase, completed work, next step.
2. Skim `docs/ROADMAP.md` and the latest `docs/PROGRESS_LOG.md` entry; check `DECISIONS.md`/`KNOWN_ISSUES.md`/`SECURITY.md` only if relevant to the task.
3. **Before building anything:** verify it isn't already implemented (grep `devos/`) — avoid duplicate work; extend existing modules, don't fork.
4. **Workflow:** `/plan` each new feature narrowly → TDD (write a failing test, watch it fail, implement, green) → run the full suite → dogfood the CLI → update all state docs + add a `D-00xx` decision if architecture changes → commit → `git push origin main`.
5. **Dev commands:**
   - Install: `pip install -e .`
   - Tests: `python -m unittest discover -s tests` (must stay green; 363 currently)
   - Isolate data in dev/tests/dogfood: set `DEVOS_HOME` to a temp dir.
   - Try it: `devos init` → `devos scan .` → `devos index .` → `devos search <q>` / `devos ask "<q>"` / `devos serve`.
6. **Guardrails:** stdlib-only runtime; mock provider default (no paid APIs); local-first/offline; grounded + no-guessing; no silent destructive writes; keep docs synchronized.
