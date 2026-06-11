# DeveloperOS — Roadmap

_Last updated: 2026-06-11_

A phased plan detailed enough that any future session can continue without rethinking
the product. Each phase lists **goal · scope · deliverables · completion criteria ·
risks · dependencies**. Status legend: ✅ done · 🚧 in progress · ⬜ not started.

---

## Phase 0 — Project Definition ✅
- **Goal:** Lock vision, scope, and foundational technical decisions.
- **Scope:** Brief, roadmap, architecture, decisions, state files.
- **Deliverables:** All mandatory `/docs` files populated; foundational decisions logged.
- **Completion criteria:** Vision restated & confirmed; 4 foundational decisions recorded; state files initialized.
- **Risks:** Over-planning; analysis paralysis. **Mitigation:** time-box, move to code.
- **Dependencies:** None.

## Phase 1 — Architecture & Scaffolding ✅
- **Goal:** A runnable, installable, tested skeleton mapping to the product modules.
- **Scope:** `devos` Python package, CLI entrypoint, config, SQLite storage layer, AI provider interface + mock, module package stubs, test harness, packaging.
- **Deliverables:** `pip install -e .` works; `devos --version`, `devos init`, `devos status` run; DB schema created; smoke tests pass; first git commit.
- **Completion criteria:** CLI runs end-to-end on a clean checkout; tests green; docs + state updated.
- **Risks:** Dependency/network friction. **Mitigation:** stdlib-only runtime.
- **Dependencies:** Phase 0.

## Phase 2 — Project Ingestion ✅
- **Goal:** Point DeveloperOS at a project folder and register/scan it.
- **Scope:** Workspace/project registry; file walker with ignore rules (.gitignore, node_modules, venvs); language/file-type classification; detect frontend/backend/db/API/auth/test/config buckets; persist project + file inventory.
- **Deliverables:** `devos scan <path>`, `devos projects`, project record + file inventory in DB.
- **Completion criteria:** Scanning a real repo produces an accurate inventory & classification; idempotent re-scan.
- **Risks:** Huge repos / binary files / encoding. **Mitigation:** size caps, binary detection, streaming.
- **Dependencies:** Phase 1.

## Phase 3 — Code Indexing & Search ✅
- **Goal:** A searchable index of code & docs.
- **Scope:** Chunking strategy (line/AST-aware later), tagging, FTS5 index, keyword search; design seam for embeddings/semantic search.
- **Deliverables:** `devos index`, `devos search <query>` (keyword), ranked results with file:line.
- **Completion criteria:** Search returns relevant results on a real repo; reindex is incremental.
- **Risks:** Index bloat; stale index. **Mitigation:** content hashing, incremental updates.
- **Dependencies:** Phase 2.

## Phase 4 — Q&A & Project Understanding ✅
- **Goal:** Answer "how does X work?" / "where is the auth flow?" with citations.
- **Scope:** Retrieval over the index → context assembly → AI provider; plain-language project explanation; module summaries.
- **Deliverables:** `devos ask "<question>"`, `devos explain [path]`, answers cite files.
- **Completion criteria:** Useful, grounded answers with file references (mock provider returns structured stub; real provider pluggable).
- **Risks:** Hallucination; context limits. **Mitigation:** retrieval-grounded prompts, citations, chunk budgets.
- **Dependencies:** Phase 3.

## Phase 5 — Debug Assistant ✅
- **Goal:** Turn an error/stack trace/log into root-cause + fix proposal.
- **Scope:** Parse traces, locate referenced files/lines, assemble context, propose cause/fix/verification; optional patch suggestion (no silent writes).
- **Deliverables:** `devos debug` (paste/pipe a trace), structured diagnosis output.
- **Completion criteria:** Correctly locates files from a real trace and produces a coherent diagnosis.
- **Risks:** Trace format variety. **Mitigation:** pluggable parsers per language.
- **Dependencies:** Phase 3 (index), Phase 4 (AI plumbing).

## Phase 6 — Task Manager & Memory ✅
- **Goal:** Track work and remember decisions across sessions.
- **Scope:** Tasks/bugs/features CRUD with status & milestones; memory store for decisions/summaries/preferences; link memory ↔ project/files; recall surfaced in search.
- **Deliverables:** `devos task ...`, `devos remember ...`, `devos recall ...`.
- **Completion criteria:** Tasks persist with status transitions; memories are searchable and recalled in Q&A.
- **Risks:** Memory sprawl. **Mitigation:** structured, deduped, compact entries.
- **Dependencies:** Phase 1 (storage); integrates with Phases 3–4.

## Phase 7 — Dashboard & Polish ✅
- **Goal:** Visual overview + UX polish (the portfolio centerpiece).
- **Scope:** TypeScript/React (Next.js) dashboard over a local API exposing projects, tasks, recent activity, blocked items, "where I left off"; CLI UX polish (Rich/Typer adoption considered here).
- **Deliverables:** Local API, dashboard app, screenshots.
- **Completion criteria:** Dashboard reflects live DB state; clean, intuitive home screen.
- **Risks:** Scope creep on UI. **Mitigation:** design pass via `ui-ux-pro-max`; ship MVP first.
- **Dependencies:** Phases 2–6 (data to display).

## Phase 8 — Documentation Automation ✅
- **Goal:** Generate docs from the indexed project.
- **Scope:** README / architecture / API / setup / changelog / decision-log / milestone-summary generators using retrieval + AI.
- **Deliverables:** `devos docgen <type>`.
- **Completion criteria:** Generated docs are accurate and useful on a real repo.
- **Risks:** Accuracy. **Mitigation:** grounded generation + human review step.
- **Dependencies:** Phases 3–4.

## Phase 9 — Future Modules ✅ (enumerated directions shipped; remains open for optional extensions)
- ✅ Slice 1: **Learning Assistant** (`devos learn <path|topic> [--level]`) — grounded leveled code explanations.
- ✅ Slice 2: **Learning Quiz** (`devos quiz <path|topic> [--n N]`) — grounded review questions.
- ✅ Slice 3: **Exercises & Grading** (`devos exercise`, `devos grade`) — grounded practice tasks + answer evaluation (feedback/strengths/weaknesses).
- ✅ Slice 4: **Career Assistant (first slice)** (`devos job`, `devos cv`, `devos interview`) — job-lead tracking, offline CV keyword match, grounded interview prep (schema v4 `job_leads`).
- ✅ Slice 5: **Plugin / Extension seam** (`devos plugins`) — entry-point + opt-in local plugins register commands/providers via existing seams; fail-safe.
- ✅ Slice 6: **Meeting / Transcript foundation** (`devos meeting summarize <file>`) — grounded summary/decisions/action-items; console-safe UTF-8 output.
- ⬜ Optional future extensions (on request): real AI providers · audio/STT · action-item→tasks · plugin sandboxing/signing · CV rewrite · multi-user/cloud.
- **Goal:** Career & Learning assistants; extension seams.
- **Scope:** Learning (explain levels, exercises, quizzes), Career (job leads, CV analysis, interview prep), plus seams for meeting assistant, multi-user, cloud sync, browser/VS Code integration, plugins, multi-agent.
- **Deliverables:** TBD per module when reached.
- **Completion criteria:** Core stable first; each module shipped behind the existing architecture.
- **Risks:** Distraction from core. **Mitigation:** do not start until Phases 1–7 are stable.
- **Dependencies:** Stable core.

---

## Post-roadmap — Dashboard slices (on-request extensions of Phase 7)
The web dashboard (`devos serve`) is being matured in narrow, individually-shipped slices on top of the
loopback API. Each reuses existing modules (no parallel engines) behind the D-0018 security controls.
- ✅ **Slice 1 — Action-oriented dashboard** (Home · Tasks · Notes · Search & Ask; guarded writes). D-0018.
- ✅ **Slice 2 — Projects tab** (list/detail + safe import/scan). D-0019.
- ✅ **Slice 3 — Debug Assistant tab** (`POST /api/debug`). D-0020.
- ✅ **Slice 4 — Project Deep Dive / Study** (`GET /api/projects/study`). D-0021.
- ✅ **Slice 5 — Settings & AI Management** (`GET /api/system`, `GET/POST /api/settings`; non-secret
  settings store + provider catalog; env-var/keychain keys only, mock default). D-0022. **(v0.5.0)**
- ✅ **Slice 6 — Learning Center** (`GET /api/learn|quiz|exercise`, `POST /api/grade`; reuses
  `modules/learning`; grounded, read-only, offline). D-0023. Fills the **Grow** IA group.
- ✅ **Slice 7 — CRUD polish** (delete tasks/notes/projects with proportional confirmation + project
  pickers + inline task-title edit; `repo.delete_project` cascade + `reconcile_fts`, index-only). D-0024.
- ✅ **Slice 8 — Career tab** (`repo` job CRUD + `career.analyze_cv`/`interview_prep`; `GET /api/jobs`,
  `GET /api/jobs/interview`, `POST /api/jobs/{create,update,delete}`, `POST /api/cv`; CV text not
  persisted). D-0025. Dashboard now at **near-CLI-parity**.
- ✅ **Slice 9 — Meeting tab** (`modules/meeting.summarize` + new deterministic
  `meeting.extract_action_items`; inline `POST /api/meeting`, transcript never persisted; action-items→
  tasks bridge reusing the guarded `POST /api/tasks/create`). D-0026. Dashboard at **full CLI parity**.
  Shipped as **v0.6.0** ("feature-complete dashboard + first real AI provider") together with: local
  **Ollama** provider behind the Settings seam (keyless, opt-in, mock stays default), **AND-first
  retrieval** (OR fallback), **secret-aware scanning**, and **GitHub Actions CI** (py3.11–3.13 ×
  Linux/Windows). Tagged **`v0.6.0`**.
- ✅ **Slice 10 — Design system + accessibility pass** (D-0027): token scales in `styles.css`
  (spacing/radius/type/motion/semantic colors; dark-only by choice; offline system fonts), WAI-ARIA
  tabs with arrow-key navigation, skip link, `role="alert"` errors, shared `Loading` primitive,
  focus-managed delete confirms with Escape, reduced-motion support; contract pinned by
  `tests/test_ui_static.py`. No new endpoints/surface.
- ✅ **Slice 11 — Onboarding / first-run** (D-0028): `WelcomeGuide` on Home — privacy/cost stated up
  front + a live six-step "Get started" checklist deep-linking into existing tabs (import → search →
  ask → learn → tasks/notes → settings); done-state data-backed from `/api/overview` or click-backed
  via localStorage; always-on while the workspace is empty, dismissible after. Fulfils
  FUTURE_ROADMAP "onboarding that earns trust in 60 seconds". Zero new endpoints.
- ✅ **Slice 12 — Desktop strategy + PWA foundation** (D-0029): chose the long-term desktop ladder —
  **PWA front + packaged Python backend** (Electron rejected; Tauri only-if-justified). Shipped step A:
  `manifest.webmanifest` (standalone, `#0f1117`, 192/512 + maskable icons), stdlib icon generator
  (`tools/make_icons.py`) + committed PNGs/SVG favicon, head wiring, `.png`/`.webmanifest` content
  types. Dashboard is now **installable from Edge/Chrome** as a desktop app. No service worker; no
  new endpoints; SECURITY unchanged. Slices 11+12 shipped together as **`v0.7.0`
  ("Installable DeveloperOS foundation")**.
- ✅ **Slice 13 — `devos app` launcher (desktop ladder step B)** (D-0030): one command for
  non-technical users — probes for a running DeveloperOS (read-only `/api/session`), reuses it or
  starts one, auto-inits a fresh home, waits for readiness, opens the browser, serves until Ctrl+C.
  Single instance per port; Windows port-occupancy handled via exclusive-bind check (SO_REUSEADDR +
  firewall-drop findings encoded in tests). No new API surface; SECURITY unchanged.
- ✅ **Slice 14 — PyInstaller packaging foundation (desktop ladder step C)** (D-0031):
  `packaging/` — spec (onefile, console, bundles `devos/api/static` + `storage/schema.sql`),
  `launch_devos.py` entry (wraps `devos app`), `build.ps1`, developer README, multi-size
  `devos.ico` (stdlib ICO writer in `tools/make_icons.py`). **Real `DeveloperOS.exe` built
  (~9.6 MB) and smoke-verified** (fresh init from bundled schema; dashboard/manifest/API from
  bundled assets; single-instance reuse). PyInstaller = dev-time only; runtime stays stdlib-only;
  SECURITY unchanged.
- ✅ **Slice 15 — Windows installer (desktop ladder step D)** (D-0032): Inno Setup per-user
  installer (`packaging/installer.iss` + `build_installer.ps1` → `DeveloperOS-Setup-<v>.exe`,
  ~11 MB) — Start-Menu shortcut, optional desktop icon, clean uninstall that **preserves user
  data** (`%APPDATA%\DeveloperOS`), manual update path via GitHub Releases (no auto-update code).
  Live-verified end-to-end (silent install → installed exe serves the dashboard → silent
  uninstall removes app+shortcut, data survives). LICENSE (MIT) added. SECURITY unchanged.
- ⬜ **Next (per `docs/FUTURE_ROADMAP.md`):** Plugins/Extensions UI (surface `devos plugins`) ·
  embeddings/semantic search behind the D-0006 seam · desktop ladder step E (Tauri)
  **only-if-justified** · optional cloud provider (Claude) **only if the no-cost policy changes**.

---

### Cross-cutting concerns (every phase)
Safe Action Agent (no destructive ops without explicit confirmation), Git Intelligence,
Terminal automation (minimum necessary commands), tests, and synchronized docs/state.
