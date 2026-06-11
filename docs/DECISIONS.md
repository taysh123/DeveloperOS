# DeveloperOS — Decision Log

_Architectural & product decisions, newest first. Each: context · decision · rationale · status._

---

## D-0029 — Desktop strategy: PWA front + packaged Python backend (slice 12 = PWA foundation)
- **Date:** 2026-06-11
- **Context:** DeveloperOS should eventually feel like an installable desktop app for
  non-technical users, without breaking the stdlib-only CLI, the loopback dashboard, the
  offline/no-cost posture, or the security model.
- **Options evaluated:**
  - *Status-quo localhost web* — zero cost but "run a command, open a browser" is not a desktop app.
  - *PWA* (manifest + icons) — tiny complexity, zero runtime size, security unchanged (same
    origin; 127.0.0.1 is a secure context so install works without HTTPS); installed PWA gives a
    real window + Start-Menu/taskbar icon today on Edge/Chrome. **Adopted now.**
  - *Electron* — ~200 MB Chromium duplicate, Node toolchain and build pipeline contradict the
    stdlib-only/no-build ethos, larger attack surface. **Rejected.**
  - *Tauri* — small (~10 MB + WebView2) but needs a Rust toolchain plus packaging the Python
    backend as a sidecar; a big complexity jump for window chrome we get from the PWA. **Deferred:
    only if a native shell (tray, file dialogs, deep OS integration) becomes necessary.**
  - *Native packaging (PyInstaller exe + Inno Setup installer)* — medium effort, no new framework,
    fits the current architecture; the realistic distribution path for the backend. **Adopted later.**
- **Decision — the desktop ladder (Windows-first, cross-platform-friendly):**
  **A)** PWA foundation (this slice): `static/manifest.webmanifest` (name "DeveloperOS" /
  short_name "DevOS", `start_url`/`scope` "/", `display: standalone`, theme/background `#0f1117`,
  192/512 + maskable icons), icon system, head wiring, `.png`/`.webmanifest` content types.
  **No service worker** — the server is local; a SW adds only cache-invalidation risk.
  **B)** `devos app` launcher: start the server + open the installed app window.
  **C)** PyInstaller single-file `devos.exe` + Start-Menu shortcut (server self-starts; PWA on top).
  **D)** Inno Setup installer; update check is **optional and manual** (point at GitHub Releases) —
  offline installs keep working forever; no cloud requirement, no auto-update daemon.
  **E)** Tauri shell **only if** step-C/D limitations demand native capabilities.
- **Branding spec:** terminal-prompt mark (`>_`) — accent `#6ea8fe` on panel `#0f1117`, drawn from
  rectangle/diagonal primitives (no font dependency; renders identically at any size); rounded
  square for normal icons, full-bleed + 78% safe-zone for maskable; SVG favicon; future multi-size
  `.ico` for the exe reuses the same mark. Generator: `tools/make_icons.py` (stdlib zlib/struct PNG
  writer — zero-dependency regeneration); generated PNGs are committed (vendored, offline).
- **Rationale:** Each ladder step is small, reversible, and keeps the existing architecture
  untouched; the web dashboard remains the single UI (no fork between "web" and "desktop" frontends);
  users get desktop ergonomics incrementally without DeveloperOS ever depending on a network,
  a paid service, or a heavyweight runtime.
- **Status:** Accepted; step A shipped in slice 12.

## D-0028 — Onboarding: welcome + live get-started checklist on Home (slice 11)
- **Date:** 2026-06-11
- **Context:** FUTURE_ROADMAP records "Onboarding that earns trust in 60 seconds" [Core]:
  folder → scan/index → first question, privacy/cost stated up front. A new user previously
  opened the dashboard to four zero-stat cards with no explanation. Patterns considered:
  first-run wizard (blocks exploration, re-embeds surfaces in a modal), guided tour (brittle
  tooltip positioning, no offline tour lib), empty-state-only hints (undiscoverable later).
- **Decision:** A `WelcomeGuide` section at the top of **Home**: two plain-language sentences
  (privacy/cost up front — "everything stays on your computer, no account, no API key") plus a
  six-step **live checklist** that deep-links into existing tabs via an `App.go(tabId)` helper
  (which also moves focus to `#main`, matching the slice-10 focus pattern). Completion state is
  **data-backed where the data exists** (`/api/overview`: project imported, task/note created —
  no new endpoint) and **click-backed otherwise** (search/ask/learn/settings, recorded in
  localStorage). Visibility rule: **always shown while the workspace is empty** (it *is* the
  Home empty state; no Hide button then), dismissible once data exists, with a persistent
  "Show the getting-started guide" link as the resurface path.
- **State storage:** one localStorage key (`devos.onboarding`, `{hidden, clicked{…}}`), wrapped
  in try/catch for storage-less browsers. Chosen over extending the `POST /api/settings`
  whitelist: it is a per-browser UI preference, not workspace data — **zero new write surface,
  CSRF/security posture untouched** (SECURITY.md intentionally unchanged).
- **Rationale:** Reuses every existing surface (ScanFlow import, Search & Ask, Learn, Tasks/
  Notes, Settings) instead of building a parallel onboarding engine; the checklist stays useful
  after first run (live progress) instead of being a one-shot modal; honest copy reinforces the
  local-first/no-cost posture at the exact moment trust is formed.
- **Status:** Accepted.

## D-0027 — Dashboard design system + accessibility contract (slice 10)
- **Date:** 2026-06-11
- **Context:** v0.6.0 made the dashboard feature-complete; the recorded next step was a
  design-system/a11y pass. The UI had good bones (dark palette vars, shared primitives,
  labeled fields, focus-visible outlines) but no token scales, no WAI-ARIA tab semantics
  beyond `aria-selected`, status-role-only messages, no skip link, no reduced-motion
  support, and sub-12px text.
- **Decision:**
  - **`styles.css` is the single design source of truth**, extended with token scales:
    spacing `--space-1..6` (4px rhythm), radii `--radius-s/m/l`, type scale (12–22px,
    body 15px, 12px floor), motion `--dur-fast/--dur-med` + ease, `--focus-ring`, and
    semantic aliases (`--danger(-soft)`, `--success(-soft)`, `--warn`, `--on-accent`)
    over the existing palette. Buttons/inputs/tabs get min-heights (44px under
    `pointer: coarse`), `:active` press states, and 150ms transitions — all collapsed by
    `@media (prefers-reduced-motion: reduce)`.
  - **Dark-only by deliberate choice** (ui-ux-pro-max design-system run for this product
    type recommends Dark/OLED and flags light-default as an anti-pattern); system font
    stack kept — **no webfonts/CDN**, the UI stays fully offline.
  - **A11y contract in `app.js`:** WAI-ARIA tabs (ids + `aria-controls` + `role="tabpanel"`
    + roving tabindex + Arrow/Home/End keys), skip link → focusable `<main>`, semantic
    `<footer>`, `Msg` errors announce as `role="alert"` (ok stays `status`), shared
    `Loading` primitive (`role="status"`, decorative spinner), `ConfirmDelete` moves focus
    into the confirm step and restores it on Escape/cancel, decorative glyphs are
    `aria-hidden`, single-field forms wire `aria-invalid`/`aria-describedby` to their error.
  - **The contract is pinned by source-level tests** (`tests/test_ui_static.py`): stdlib
    has no DOM runtime, so tests assert the served sources carry the tokens/roles/handlers;
    runtime behavior is covered by live socket smoke + a manual keyboard pass per slice.
- **Rationale:** Polish and accessibility as a durable contract rather than a one-off
  sweep; zero new endpoints or write surface (SECURITY unchanged); all existing components
  refined in place, preserving the no-build vendored architecture (D-0010/D-0018).
- **Status:** Accepted.

## D-0026 — v0.6.0: Meeting tab (slice 9) + Ollama provider + AND-first retrieval + secret-aware scan + CI
- **Date:** 2026-06-11
- **Context:** The dashboard's last CLI-parity gap was the Meeting surface (recorded next step after
  D-0025), and the Settings seam (D-0022) had providers catalogued but only the offline mock wired.
  Retrieval was OR-only (KNOWN_ISSUES) and SECURITY §2 carried a PLANNED "secret-aware indexing" item.
  The work was built TDD in a detached working copy and merged into this repo (tree-hash verified, no
  loss) in the v0.6.0 release session.
- **Decision:**
  - **Meeting tab (slice 9):** `modules/meeting.extract_action_items` (deterministic — bulleted lines
    under an "Action items"/"Next steps" heading or `TODO:`/`Action:`/`Next step:` prefixes; **never
    calls a provider**) + `app.py` `meeting_payload` and inline `POST /api/meeting` (multi-line
    transcript, like `/api/debug`; transcript **not persisted**; inherits the D-0018 CSRF/Origin/JSON/
    64 KB guards). UI: a **Meeting** tab with summary/decisions/action-items cards and an
    `ActionItemsBridge` that creates selected items as tasks by reusing the guarded
    `POST /api/tasks/create` — **no new write surface**.
  - **Ollama provider:** `devos/providers/ollama.py` (`OllamaProvider.complete`/`ping`) against a local
    daemon (`http://127.0.0.1:11434` default; `DEVOS_OLLAMA_URL`/`DEVOS_OLLAMA_MODEL`), stdlib `urllib`
    only, registered via `providers/__init__` import (the same seam plugins use). Unreachable daemon →
    clearly-labeled "[OLLAMA UNAVAILABLE]" `AIResult` (`meta.ok=False`) with fix instructions, never an
    exception. **Default unchanged:** the effective provider remains the offline mock unless the user
    deliberately selects Ollama in Settings.
  - **AND-first retrieval:** `qa.retrieve` tries `op="AND"` first (multi-term queries only) and falls
    back to `op="OR"`, preserving the old recall while strongly preferring tight grounding.
  - **Secret-aware scan:** `ingest.SECRET_FILE_PATTERNS` + `is_secret_file` skip credential-looking
    files **before stat/read**; `ScanResult.skipped_secrets` reports the count (closes the SECURITY §2
    PLANNED item).
  - **CI:** `.github/workflows/ci.yml` — the stdlib unittest suite on every push/PR, matrix
    py3.11–3.13 × Linux/Windows.
  - Version **0.5.0 → 0.6.0**.
- **Rationale:** Closes CLI parity and ships the first real provider without breaking the no-cost,
  local-first, offline-by-default posture (SECURITY §0/§1): Ollama is local/free/keyless and opt-in;
  the deterministic extractor plus CV-style non-persistence keep the new surface minimal; AND-first
  improves grounding precision exactly where a real model benefits; secret skipping closes a recorded
  gap before any real model ever sees indexed text.
- **Status:** Accepted (v0.6.0).

## D-0025 — Dashboard Career tab (`/api/jobs*`, `/api/cv`)
- **Date:** 2026-06-03
- **Context:** The Career Assistant (`modules/career` + `repo` `job_leads` CRUD) — job-lead tracking,
  deterministic offline CV keyword analysis, and grounded interview prep — was CLI-only (`devos
  job/cv/interview`). Surface it in the dashboard (recorded next slice) without a parallel engine.
- **Decision:**
  - **Reads:** `GET /api/jobs?status=` (reuse `repo.list_jobs`); `GET /api/jobs/interview?id=&n=`
    (read-only AI via `ws.ai`, reuse `career.interview_prep`; grounded on the lead's notes, **declines
    when noteless**; `n` clamped 1–15; unknown id → 404).
  - **Writes:** `POST /api/jobs/{create,update,delete}` registered in `_POST_ACTIONS` (inherit the D-0018
    CSRF/Origin/JSON/64 KB guards). `create` requires `company` and validates `status ∈ repo.JOB_STATUSES`;
    `update`/`delete` validate a positive int id (400) and 404 unknown. Reuse `repo.create_job`/
    `update_job`/`delete_job`. No schema change (`job_leads` shipped in schema v4).
  - **`POST /api/cv`** handled **inline in `route()`** (multi-line CV text, like `/api/grade`):
    **deterministic, offline** keyword coverage via `career.analyze_cv` against either a selected lead's
    `notes` (`job_id`) or a pasted `target_text`. **The CV text is treated as untrusted DATA and is never
    persisted** (stateless analysis, no provider call). Returns matched/missing (sets → sorted lists),
    coverage, counts, target label.
  - **UI:** a **Career** tab (IA "Grow" group, beside Learn) with three friendly sections — Track a job
    application (CRUD with inline status select + edit + the slice-7 `ConfirmDelete` two-step), Interview
    prep (lead → grounded questions; friendly decline), and CV match check (coverage % + matched/missing
    keyword chips). Reused existing components/CSS; no new CSS.
- **Rationale:** Maximum reuse of the existing career engine and the secure write boundary; job leads are
  personal data already stored locally (SECURITY §5/§9); CV text and job notes are data-not-instructions;
  interview prep is grounded and declines rather than guessing. No new outbound surface; offline/mock.
- **Status:** Accepted (dashboard slice 8). Career follow-ups (CV rewrite / cover letters; portfolio
  bullets; mock-interview mode) remain **on-request** (see `docs/FUTURE_ROADMAP.md`). Job-board
  scraping/APIs remain intentionally excluded.

## D-0024 — Dashboard CRUD polish (delete endpoints, project pickers, inline edit)
- **Date:** 2026-06-02
- **Context:** The dashboard could create/update tasks & notes and import projects, but a non-CLI user
  couldn't **delete** anything, choose a new item's **project**, or rename a task in place. This is the
  recorded next slice (CRUD polish). Goal: everyday practicality with **zero parallel CRUD engine**.
- **Decision:**
  - **`repo.delete_project(conn, id)`** (new): a single `DELETE FROM projects` relies on the existing
    `ON DELETE CASCADE` foreign keys (files → chunks, tasks, memory; `PRAGMA foreign_keys` is enabled in
    `db.connect`) and then calls the existing **`reconcile_fts`** to purge the FTS5 mirror (a virtual table
    not covered by cascades). **Index-only — it never deletes the user's files on disk.** `delete_task`
    and `delete_memory` already existed and are reused as-is.
  - **`POST /api/tasks/delete`, `/api/notes/delete`, `/api/projects/delete`** registered in the existing
    `_POST_ACTIONS` table (so they inherit the D-0018 CSRF token + Origin allowlist + JSON-only + 64 KB
    guards — **no `server.py` change**). Shared `_require_id` validates a positive int id → 400; unknown →
    404 (via `get_task`/`get_memory`/`get_project`); success returns `{"deleted": n}`. No schema change.
  - **Project pickers** are **frontend-only** — `create_task_action`/`create_note_action` already accept a
    `project` name (resolved via `_resolve_project`). Inline **task-title** edit reuses `tasks/update`.
  - **UI:** a reusable **two-step `ConfirmDelete`** for the low-impact task/note deletes; project deletion
    is gated behind a **type-to-confirm** (must type the project name) **danger zone** on the project
    detail, with a warning that disk files are untouched. Reused existing components/CSS + a small danger
    style. **Confirmation strength chosen with the user:** lightweight for tasks/notes, strict
    type-to-confirm for the cascading, high-impact project delete.
- **Rationale:** Reuses the secure write boundary and storage layer end-to-end; the only new storage code
  is one cascade-aware `delete_project`. Destructive actions require explicit, proportional confirmation;
  the most destructive (project, which cascades to its tasks/notes) is the hardest to trigger and is
  clearly scoped to DeveloperOS's own data.
- **Status:** Accepted (dashboard slice 7). Future: undo/soft-delete, bulk actions, and reassigning an
  existing task/note's project remain **on-request** (see `docs/FUTURE_ROADMAP.md`).

## D-0023 — Dashboard Learning Center (`/api/learn|quiz|exercise|grade`)
- **Date:** 2026-06-02
- **Context:** The Learning Assistant (`modules/learning`: `learn`/`quiz`/`exercise`/`grade`) — grounded,
  leveled explanations, review questions, practice exercises, and answer grading — was CLI-only. It's the
  "Grow" group of the recorded dashboard IA (D-0021) and the next prioritized slice. Surface it for
  non-programmers without a parallel engine.
- **Decision:**
  - **Payload builders** (`learn_payload`/`quiz_payload`/`exercise_payload`/`grade_payload`, sharing a
    `_chunk_sources` serializer) wrap `modules/learning` 1:1 (topic/level/n, text, grounded, provider,
    `file:line` sources).
  - **`GET /api/learn?target=&level=&project=`**, **`GET /api/quiz?target=&n=&project=`**, and
    **`GET /api/exercise?target=&n=&project=`** are read-only (reuse `ws.ai`, like `/api/ask`/`/api/explain`).
    `target` is required → friendly 400; `level` validated against `learning.LEVELS`; `n` clamped (quiz
    1–20, exercise 1–10) via the existing `_int` helper.
  - **`POST /api/grade` `{target, answer, question?, project?}`** is **read-only** but uses POST because the
    learner's answer is multi-line free text (same rationale/placement as `/api/debug` — handled inline in
    `route()`'s POST branch, before `_POST_ACTIONS`). Validates non-empty string `target`/`answer` → 400.
    Inherits the D-0018 CSRF token + Origin allowlist + JSON-only + 64 KB guards. No `server.py` change.
  - **UI:** a **Learn** tab (… · Projects · **Learn** · Settings) — target input + project dropdown +
    depth select; **Explain it / Quiz me / Give me exercises** buttons; and a **Check my understanding**
    answer box. A shared `AnswerBlock` renders grounded text + sources with an honest ungrounded note.
    Reused existing components/CSS; no new CSS.
- **Rationale:** Pure reuse of the grounded learning pipeline (`qa.retrieve`/`assemble_context` + provider),
  which already declines (no provider call) when nothing is indexed and derives `file:line` attribution
  from retrieval (SECURITY §5). No new write surface, no new outbound calls, offline/mock default.
- **Status:** Accepted (dashboard slice 6). Persisted progress (quiz/exercise scores) and a guided
  "learn this repo" path remain **on-request** (see `docs/FUTURE_ROADMAP.md`).

## D-0022 — Dashboard Settings & AI Management (`/api/system`, `/api/settings`) + settings store
- **Date:** 2026-06-02
- **Context:** The dashboard had no way to see or control AI behavior; provider selection lived only in
  the `DEVOS_AI_PROVIDER` env var and `ws.ai`. Slice 5 (the recorded next priority, D-0021) surfaces and
  controls this for non-technical users — **without** introducing a parallel provider system or storing
  any secret.
- **Decision:**
  - **New `devos/settings.py`** holds **non-secret preferences only** (`ai_enabled`, `ai_provider`) in
    `<data_dir>/settings.json` (no schema migration; data dir already git-ignored). A `PROVIDERS` catalog
    (`mock`, `ollama`, `claude`, `openai`) carries privacy (`local`/`cloud`) + cost (`free`/paid) +
    `key_env` metadata that drives the UI. `save()` is **keyword-only on the two fields** so a secret can
    never be written; unknown providers raise. `effective_provider_name(preferred, enabled)` resolves the
    provider **actually used**, falling back to the offline `mock` when AI is disabled or the choice isn't
    registered in `providers.ai.available_providers()` yet — so selecting Claude/OpenAI/Ollama is a stored
    *preference* with **no external call and no key required** until a real provider ships.
    `key_present(id)` returns a **boolean** read from the environment — never the value.
  - **Reuse, not fork:** `config.load_config()` resolves `DEVOS_AI_PROVIDER` env → `settings.json` → `mock`
    and adds `ai_enabled`; `Workspace.ai` goes through `effective_provider_name`. Backward compatible —
    defaults keep `ws.ai == mock`, so the whole existing suite stays green.
  - **API:** read-only `GET /api/system` (local-first/offline/ai_enabled/provider selected+effective/
    `version`/roadmap phase/indexed project count/dashboard maturity + catalog) and `GET /api/settings`
    (catalog + per-provider `available`/`key_present`). `POST /api/settings` is handled **inline in
    `route()`** (it writes the JSON file and needs `ws`, not `conn` — same pattern as `/api/debug`); it
    **reads only `ai_enabled`/`ai_provider`** from the body (any `api_key`/`endpoint` is ignored) and
    inherits the D-0018 CSRF token + Origin allowlist + JSON-only + 64 KB guards. No `server.py` change.
  - **UI:** a **Settings** tab — System status rows, an AI enable toggle + provider radio list (Local/Cloud
    + Free/Paid badges, Coming-soon + key-detected hints, plain-language privacy/cost notes), and a
    **prepared but disabled** provider-config panel (API key / endpoint / model) with helper text that
    keys come from environment variables and are never stored.
  - **Version 0.1.0 → 0.5.0** (five shipped dashboard slices), surfaced in System status + `devos --version`.
- **Rationale:** Maximum reuse of the single provider registry; secrets stay out of SQLite/JSON/frontend
  (SECURITY §2 — env vars / OS keychain only, presence-boolean exposure); safe graceful fallback to
  offline mock keeps the default private/free/no-key; no new outbound surface.
- **Status:** Accepted (dashboard slice 5). Real provider integrations / key input / endpoint persistence
  remain **on-request** and out of scope here.

## D-0021 — Dashboard Project Deep Dive / Study (`GET /api/projects/study`) + long-term roadmap
- **Date:** 2026-06-02
- **Context:** The dashboard could import/view projects but not help a beginner *understand one deeply*
  (for learning / interview prep). Add a Study experience by **aggregating existing grounded modules** —
  no new analysis engine.
- **Decision:**
  - **`study_payload(conn, ws, project_id, n=6)`** bundles, by pure reuse: project facts (from
    `repo.list_projects`), `categories` (`repo.category_breakdown`), `key_files` (`repo.top_files`),
    an `overview` (**`qa.explain`** project overview), grounded `questions` (**`learning.quiz`** on the
    top key file, else the project name), and a **deterministic, offline `interview_prep`** checklist
    derived from name + key files + top categories (no provider call).
  - **`GET /api/projects/study?id=&n=`** (read-only, beside `/api/projects/detail`): `id` validated as a
    digit → 400, unknown → 404, `n` clamped 1–20. Downstream project name/paths come from the DB
    (resolved from the integer id), not raw client text. No `server.py` change.
  - **UI:** a **Study this project** button on the project detail opens a **Project Deep Dive** view
    (sections: Start here · Key files · How this works · Questions to explore · Interview prep) plus an
    **Ask about this project** box reusing `GET /api/ask?project=`. Kept as a project sub-section this
    slice (may graduate to a top-level tab later).
  - **Long-term dashboard roadmap recorded** (see the plan / AGENT_STATE): IA grouping (Work · Understand
    · Grow · System) and prioritized future slices — Settings + AI-provider toggle (reuse the existing
    `get_provider(config.ai_provider)` / `ws.ai` seam; keys from env/keychain only, mock default), then
    Learning, CRUD polish, Career, Meeting, Plugins UI, design/a11y polish.
- **Rationale:** Maximises reuse (`qa.explain` + `learning.quiz` + `repo` structure helpers), stays
  read-only/index-only/offline, and degrades gracefully for unindexed projects. Deterministic interview
  checklist avoids a second provider call and works offline.
- **Status:** Accepted (dashboard slice 4). Future slices remain on-request (Part 1 of the plan).

## D-0020 — Dashboard Debug Assistant tab (`POST /api/debug`)
- **Date:** 2026-06-02
- **Context:** The Debug Assistant (`modules/debug.diagnose`) — paste an error/trace/log → grounded
  root-cause + fix with `file:line` evidence — was CLI-only (`devos debug`). Surface it in the dashboard
  for non-programmers without a parallel debugging engine.
- **Decision:**
  - **`debug_payload(conn, ws, trace_text, project=None)`** serializes `DebugDiagnosis` (error_type/
    message, frames, located frames, analysis, confidence, grounded, provider, sources) to JSON.
  - **`POST /api/debug`** `{trace, project?}`: **read-only** (no DB write) but uses POST because the
    trace/log is multi-line text (awkward/oversized for a GET query string). Handled **inline in
    `route()`'s POST branch** (it needs `ws.ai` and is read-only — unlike the DB-write `_POST_ACTIONS`),
    **before** the `_POST_ACTIONS` lookup. Validates `trace` is a non-empty string → friendly 400.
    Inherits the D-0018 CSRF token + Origin + JSON-only + 64 KB guards.
  - **`server.py` `do_POST` hardening (incidental):** read the bounded request body **before** the
    auth checks so an early rejection can't desync the HTTP/1.1 keep-alive connection (was an
    intermittent client-side connection reset instead of a clean status); size-cap rejections now
    send `Connection: close`. Behavior-preserving; fixes a pre-existing flaky test.
  - **UI:** a **Debug** tab (Home · Tasks · Notes · Search & Ask · Debug · Projects) — a large paste
    area + **Analyze** + Clear, loading/error/empty states, and result cards: summary (error +
    confidence badge), "What we think is going on" (the grounded analysis; friendly note when
    ungrounded), "Where it points" (located frames), and "Sources" (attribution).
- **Rationale:** Pure reuse of `debug.diagnose` (which reuses `qa.retrieve`/`assemble_context` +
  `trace.parse_trace`). The pasted trace is untrusted **data, not instructions** (grounding contract,
  §5); file location stays **index-only** (never reads trace-named paths); the diagnosis is **not
  persisted**. Offline, mock provider unchanged.
- **Status:** Accepted (dashboard slice 3). Learning/Career/Meeting UIs and persistence remain on-request.

## D-0019 — Dashboard Projects tab: safe import/scan + project overview
- **Date:** 2026-06-02
- **Context:** After the action slice (D-0018), onboarding a project still required the CLI
  (`devos scan`). To make the dashboard a complete entry point, non-programmers need to import and
  view projects from the UI — reusing existing scan/index logic, without weakening security.
- **Decision:**
  - **`GET /api/projects/detail?id=`** → `project_detail` builder reusing `repo.list_projects`
    (already computes `file_count`), `repo.category_breakdown`, and `repo.chunk_stats`
    (indexed chunks/files). Unknown id → 404; missing/invalid id → 400.
  - **`POST /api/projects/scan`** `{path, name?}` → `scan_project_action`: validates `path` is a
    non-empty string (≤ 4096 chars), runs **`ingest.scan_project`** (which resolves + `is_dir()`-
    validates the path and applies the existing ignore/size/binary rules) then
    **`index_mod.index_project`**, returning the `ScanResult` summary + indexed chunk count.
    Non-directory/missing path → friendly **400**. Registered in `_POST_ACTIONS`, so it inherits the
    D-0018 CSRF-token + Origin + JSON-only + 64 KB guards (**no `server.py` change**).
  - **Import = scan + index** (one action) so an imported project is immediately usable in Search &
    Ask — the right default for a non-programmer's "Import Project."
  - **UI:** new **Projects** tab (Home · Tasks · Notes · Search & Ask · Projects) with list / detail /
    import sub-views. Import is a **two-step, confirm-before-write** flow (explain → enter path →
    confirm panel echoing the exact path → "Scan now"); detail shows name, folder, file count, last
    scanned, indexed status, and a category breakdown, with a **Re-scan** action.
- **Rationale:** No new scanner — pure reuse of `ingest`/`index`/`repo`. Path is untrusted and
  validated server-side; the browser-triggerable scan is already gated by the D-0018 controls
  (loopback + token + origin + no-CORS), so a cross-origin page can't trigger it. Reads only local
  files the user explicitly names — functionally identical to CLI `devos scan` (same §2 secret
  caveat). Offline, mock provider unchanged.
- **Status:** Accepted (dashboard slice 2). Debug/Learning/Career/Meeting UIs and project deletion
  remain on-request.

## D-0018 — Action-oriented dashboard: guarded write API (token + CSRF) over loopback
- **Date:** 2026-06-02
- **Context:** The Phase 7 dashboard was read-only (GET); everyday work still required the CLI. To make
  the dashboard the primary, non-programmer-friendly entry point we needed the API to perform common
  actions. SECURITY.md §8 had pre-committed the controls for this exact moment.
- **Decision:**
  - **Extend `app.route(ws, path, query, *, method="GET", body=None)`** (keyword-only `method`/`body`
    keeps every existing GET call site unchanged). New **POST** actions reuse existing repo writes:
    `/api/tasks/create`, `/api/tasks/update`, `/api/notes/create`, `/api/notes/update`; new read-only
    **GET** endpoints surface existing modules: `/api/search` (`index.search`, OR-mode),
    `/api/ask` (`qa.answer`), `/api/explain` (`qa.explain`) — provider via `ws.ai` (mock default).
  - **Added `repo.update_memory`** (the only missing reusable fn), mirroring `update_task`'s
    `_MEMORY_UPDATABLE` whitelist + parameterized SQL.
  - **Security at the HTTP boundary (`server.py`, stdlib only):** per-server CSRF token
    (`secrets.token_urlsafe`) delivered same-origin via `GET /api/session` and required in the
    `X-DevOS-Token` header (constant-time compare); **Origin allowlist** (loopback only); JSON
    content-type required; **64 KB** request cap. **No CORS headers** are ever emitted, so a
    cross-origin page can neither read responses nor obtain the token. Loopback binding unchanged.
  - **Input validation at the API layer** (friendly 400s): required/length-capped titles, enum checks
    for status/kind/priority, unknown-project rejection, positive-int ids.
  - **Frontend:** the vendored React+htm SPA gains lightweight **tabbed navigation** (Home · Tasks ·
    Notes · Search & Ask) — state-driven, no router, no new deps — with accessible labels and a shared
    token-aware `post()` helper.
- **Rationale:** Builds the reusable secure-write foundation once; rides it for the two simplest fully
  offline actions (tasks/notes) and exposes existing read-only search/Q&A. DB record writes are
  equivalent to the existing CLI `task`/`remember` mutations, so they do **not** invoke the Safe Action
  Agent (§4), which stays reserved for filesystem/git/shell. Stays stdlib-only, local-first, offline.
- **Status:** Accepted (dashboard slice 1). Scan/debug/learning/career/meeting UIs remain on-request.

## D-0017 — Phase 9 slice 6 = Meeting/Transcript foundation (+ console-safe output)
- **Date:** 2026-06-01
- **Context:** Final enumerated Phase 9 direction: summarize a local transcript/notes file. Completes learning+career+plugin+meeting.
- **Decision:**
  - **`modules/meeting.summarize(text, *, provider, source_label)` → `MeetingSummary`** — grounded Summary/Decisions/Action-items via the provider seam; transcript is **data, not instructions**; declines (no provider call) on empty input; context capped at `MAX_TRANSCRIPT_CHARS=12000`. **No schema change; transcript not persisted (read-only).**
  - **`devos meeting summarize <file>`** (nested subcommand "foundation" namespace); reads only the user-named path with **`utf-8-sig`** (strips Windows BOM); prints summary + `Source:`.
  - **Cross-cutting fix:** `cli.main` now reconfigures stdout/stderr to **UTF-8 with replacement** (guarded; skipped for non-reconfigurable streams like test `StringIO`), so echoing non-cp1252 content (BOM, smart quotes, emoji) no longer crashes `print()` on a Windows console — benefits every content-echoing command.
- **Status:** Accepted (slice 6). All originally-enumerated Phase 9 directions now shipped; further extensions (audio STT, action-item→tasks, plugin sandboxing, CV rewrite) remain optional/on-request.

## D-0016 — Phase 9 slice 5 = Plugin / Extension Seam
- **Date:** 2026-06-01
- **Context:** Fulfil the "open architecture" goal: let external packages/opt-in local files extend DeveloperOS without forking. (Header/body of the request conflicted; user confirmed Plugin System, since Career was already shipped.)
- **Decision:**
  - **Reuse existing registries** — plugins register commands via `commands.base.register` (auto-picked by `cli.build_parser`) and AI providers via the new public `providers.ai.register_provider`. No parallel machinery, no schema change.
  - **`devos/plugins.py`:** discovery from (a) entry-point group `devos.plugins` (each resolves to a zero-arg registration callable) — always loaded; (b) `<data_dir>/plugins/*.py` — loaded **only when `DEVOS_ENABLE_LOCAL_PLUGINS=1`** (opt-in; off by default). `ensure_loaded()` runs once at `cli.main` startup, guarded; failures are isolated into `ERRORS` (never crash the CLI), successes into `LOADED`.
  - **`devos plugins`** lists loaded plugins + errors. `load_entry_point_plugins(eps=...)` accepts injected entry points for testing.
  - **Security (new surface):** loading plugins executes third-party code — a supply-chain/code-execution risk (first in the project). Entry-point plugins = packages the user installed (trusted); local `.py` are opt-in only. Documented in SECURITY.md; sandbox/signing deferred.
- **Status:** Accepted (slice 5). Remaining Phase 9 slice (meeting/transcript) deferred pending approval.

## D-0015 — Phase 9 slice 4 = Career Assistant (first slice)
- **Date:** 2026-06-01
- **Context:** First Career slice (user-approved): job-lead tracking, offline CV keyword matching, grounded interview prep — no scraping/paid APIs.
- **Decision:**
  - **Schema v4: `job_leads`** table (company/role/url/status/notes/timestamps); `schema.sql` + `MIGRATIONS[4]` + `SCHEMA_VERSION=4`; added to `db.COUNTED_TABLES` (shown in `devos status`).
  - **Job CRUD in `storage/repo`** mirroring tasks (`create_job`/`get_job`/`list_jobs`/`update_job`/`delete_job`, `JOB_STATUSES`); `devos job add/list/show/set/rm`.
  - **`modules/career.analyze_cv(cv_text, target_text)`** — deterministic, offline keyword overlap reusing `qa.question_terms` (matched/missing/coverage). `devos cv <file> [--job ID]` matches a local CV against a job's **notes** (the description; company/role excluded to avoid noise) or all jobs' notes. No AI.
  - **`career.interview_prep(conn, job_id, *, provider, n)`** — grounded interview questions from the job's stored notes via the provider seam; declines (no provider call) when the job is missing/noteless; `n` clamped [1,15]. `devos interview <job-id>`.
  - **Local-first/private:** job leads + CV text are personal data; job CRUD writes only to the local DB; `cv`/`interview` are read-only; `--file` reads only the user-named path. No scraping/external/paid APIs.
- **Status:** Accepted (Career slice 1). Remaining Phase 9 slices (plugin seam, meeting/transcript) deferred pending approval.

## D-0014 — Phase 9 slice 3 = Learning Exercises & Grading (`devos exercise` / `devos grade`)
- **Date:** 2026-06-01
- **Context:** Third narrow Phase 9 slice (user-approved), completing the Learning module's practice loop.
- **Decision:** Add `exercise()`/`Exercise` and `grade()`/`Grade` to `modules/learning.py`, reusing the shared `_resolve_chunks` + `qa.assemble_context` + provider seam. `exercise` generates `n` grounded practice tasks (default 3, clamped [1,10]). `grade` evaluates a learner's supplied answer against freshly-retrieved code (the ground truth) and returns Feedback / Strengths / Weaknesses with file:line sources. **Stateless & read-only — no persistence, no schema change** (saving scores/exercises to memory is deferred). Both decline (no provider call) when ungrounded; `grade` requires a non-empty answer (ValueError otherwise). Learner answer + code are treated as DATA, not instructions (grounding/anti-injection posture). `devos exercise`/`devos grade` reuse `ask_cmd.print_answer`.
- **Status:** Accepted (slice 3). Remaining Phase 9 slices (Career, plugin seam, meeting/transcript) still deferred pending approval.

## D-0013 — Phase 9 slice 2 = Learning Quiz (`devos quiz`)
- **Date:** 2026-06-01
- **Context:** Second narrow Phase 9 slice (user-approved), building on slice 1's Learning Assistant.
- **Decision:** Add `quiz()` + `Quiz` to `modules/learning.py` (cohesive with `learn`). Extracted the shared target→chunks logic into `_resolve_chunks` (used by both `learn` and `quiz`) — DRY, **no new retrieval logic, no schema change**. `quiz` generates `n` grounded review questions (default 5, clamped to [1,20]; `n<1` → ValueError) from file-mode or topic-mode chunks; declines (no provider call) when ungrounded; cites file:line. `devos quiz` reuses `ask_cmd.print_answer`; stdout/read-only. Same grounding/anti-injection posture as `learn`.
- **Status:** Accepted (slice 2). Remaining Phase 9 slices (career, plugin seam, meeting/transcript) still deferred pending approval.

## D-0012 — Phase 9 delivered as slices; slice 1 = Learning Assistant (`devos learn`)
- **Date:** 2026-06-01
- **Context:** Phase 9 ("future modules") is open-ended. To avoid scope creep we deliver it as **narrow, separately-approved slices**. Slice 1 (user-selected) is the Learning Assistant.
- **Decision:**
  - **`modules/learning.learn(conn, target, *, provider, level, project, limit)` → `Lesson`** gives a grounded, leveled explanation. **File mode** (target resolves to an indexed file via `repo.find_project_for_path`/`find_file_by_path`/`get_file_chunks`) grounds on that file's chunks; **topic mode** grounds via `qa.retrieve`. Declines (no provider call) when ungrounded. Same composition pattern as `debug`/`docgen` — **no new retrieval logic, no schema change.**
  - **Levels** `eli5`/`intermediate`(default)/`advanced` = different system-prompt guidance over identical grounded context. Grounding/anti-injection contract preserved (context is data; attribution from retrieval; cite file:line).
  - **`devos learn <target...>`** prints via the shared `ask_cmd.print_answer` (text + deduped file:line Sources); stdout only (read-only).
  - **Remaining Phase 9 directions (quizzes/exercises, career, plugin seam, meeting/transcript) are deferred** and require separate approval. ROADMAP Phase 9 stays in-progress (🚧), not done.
- **Status:** Accepted (slice 1).

## D-0011 — Documentation Automation: grounded docgen reusing the Q&A pipeline
- **Date:** 2026-06-01
- **Context:** Phase 8 generates project docs without a parallel pipeline, staying grounded/offline.
- **Decision:**
  - **`modules/docgen.generate(conn, doc_type, *, provider, project, limit)`** with two grounding families: code docs (`readme`/`architecture`/`api`/`setup`) ground on **`qa.retrieve`** (type-specific seed query) + project facts (`repo.category_breakdown`/`top_files`); record docs (`changelog`/`decisions`/`milestone`) ground on `repo.list_memory`/`list_tasks`. Both → `qa.assemble_context`-style context → one `provider.complete()` → `GeneratedDoc`. No new retrieval logic.
  - **Grounded / no-guess:** ungrounded types (nothing indexed / no records) return `grounded=False` with a clear message and **no provider call**.
  - **Record docs include global (project-less) memory/tasks** for the resolved project (added `include_global` to `repo.list_memory`/`list_tasks`), so user-recorded decisions surface even when not project-scoped.
  - **Output safe by default:** stdout; `--output PATH` writes but **never overwrites without `--force`** (no silent writes, SECURITY §4). Generated text is model output, never executed. Attribution (file:line / record titles) from retrieval/records, not the model.
  - Provider-agnostic via `providers.ai` (mock default); future real providers improve prose unchanged. A future dashboard/API can call `docgen.generate` directly.
- **Status:** Accepted.

## D-0010 — Dashboard: stdlib http.server local API + vendored React SPA (offline, read-only)
- **Date:** 2026-06-01
- **Context:** Phase 7 adds a dashboard. Needed a UI that stays local-first/offline/verifiable and reuses existing layers (no parallel backend), consistent with the stdlib-only ethos (D-0005).
- **Decision:**
  - **Local API = stdlib `http.server`** (`devos/api/server.py`, `ThreadingHTTPServer`), **bound to 127.0.0.1 only** and **read-only (GET)** this phase. No web framework dependency.
  - **Socket-free, testable core:** `devos/api/app.py` holds pure data builders (`overview`/`projects_payload`/`tasks_payload`/`memory_payload`/`recall_payload`) reusing `storage/repo` + `modules.recall`, and a `route(ws, path, query) -> Response` table unit-tested without binding a port; `server.py` is a thin wrapper (one live integration test).
  - **Frontend = React + `htm` (no JSX build), vendored** under `devos/api/static/vendor/` (downloaded once from unpkg, committed) → fully offline, no npm/Node, no CDN at runtime. Served as static assets (path-traversal-safe). User-selected over a full Next.js app to preserve offline/zero-build/verifiable properties.
  - **`devos serve`** runs the dashboard (loopback); `"where I left off"` is derived from the DB (latest in-progress/most-recent task + recent memory), not docs.
- **Rationale:** Ships a genuine React dashboard that is offline, dependency-free at runtime, fully testable in the existing harness, and reuses every data/service layer. Architecture stays expansion-ready (route table + loopback + read-only; future write endpoints need a token/CSRF per SECURITY §8).
- **Status:** Accepted.

## D-0009 — Task Manager & Memory: schema v3, repo CRUD, retrieval-only recall
- **Date:** 2026-06-01
- **Context:** Phase 6 activates the reserved `tasks`/`memory` tables with CRUD + cross-source recall, reusing existing layers (no parallel system, no dashboard).
- **Decision:**
  - **`tasks.priority` = TEXT `low|medium|high` (default `medium`)** — schema **v3**: `schema.sql` for fresh DBs + `MIGRATIONS[3]` ALTER for existing DBs (numbered-migration runner from D-0006-era `db.initialize`).
  - **CRUD lives in `storage/repo.py`** (matching the established SQL-in-repo pattern): `create_task/get_task/list_tasks/update_task/delete_task/search_tasks` and `create_memory/get_memory/list_memory/delete_memory/search_memory`. Commands call repo directly (CRUD is thin); orchestration (recall) is a module.
  - **`recall` (modules/recall.py) is retrieval-only and offline** — groups memory + tasks (SQL `LIKE`) with code (**reusing `qa.retrieve`** → FTS). No AI call → no new prompt-injection surface (SECURITY.md §5). Empty query lists recent memory/tasks.
  - **Tasks/memory search via SQL `LIKE`** (no new FTS table) — sufficient at single-user scale; can upgrade to FTS later.
  - **Idempotency:** `create_memory` dedups on `(project_id, title, body)` (returns existing id); task creation is additive; `update_task`/`set` operations are idempotent.
  - **Project linkage optional** (`project_id` NULL = global); resolve `--project` by name, unknown name → error.
  - **`devos task`** uses nested argparse subcommands (`add|list|show|set|rm`); thin `repo` functions keep a future API/dashboard able to call the same layer.
- **Rationale:** Delivers the Project Manager + Memory Engine on the existing schema/storage with one tiny migration, stays offline/local-first, and keeps recall safe by avoiding any model call.
- **Status:** Accepted.

## D-0008 — Debug Assistant: pluggable trace parsing + index-only location, reusing retrieval
- **Date:** 2026-06-01
- **Context:** Phase 5 turns errors/traces/logs into diagnoses. Must be useful, grounded, safe with untrusted input, and reuse existing layers (no duplicate retrieval), with no schema change.
- **Decision:**
  - **Pure, pluggable parsing in `modules/trace.py`:** `parse_python`/`parse_node`/`parse_generic` registered in `TRACE_PARSERS`; first parser yielding frames wins, else a generic `path:line` scan. New languages = new parser fn, no other change.
  - **`modules/debug.diagnose`** orchestrates: parse → **locate frames in the index only** (`repo.find_file_by_path`; absolute paths via `find_project_for_path`) → **reuse `qa.retrieve`** for related code and **`qa.assemble_context`** for context → generate via `providers.ai`.
  - **Security — no filesystem egress:** trace-supplied paths are resolved only against the DB index; DeveloperOS never opens a path named in a trace. An absolute path outside any known project is skipped. (SECURITY.md §5.)
  - **Structured, grounded output:** `DebugDiagnosis` separates deterministic evidence (`error_type`/`error_message`/`frames`/`located_frames`/`sources`) from the provider's `analysis` (system prompt mandates Observed evidence / Likely root cause / Assumptions / Recommended fix / Verification steps + file:line + low-confidence honesty). Heuristic `confidence`: high (a frame located with its code), medium (related code only), low (nothing → decline, no provider call). Attribution from parsing/retrieval, never the model.
  - **Provider readiness:** reuses the D-0007 `providers.ai` seam; real Claude/OpenAI/Ollama improve `analysis` with no debug-code change. No schema change (read-only over the index).
- **Rationale:** Delivers a safe, grounded debugger now on stdlib + mock; the parser registry and provider/retrieval reuse keep it extensible without redesign.
- **Status:** Accepted.

## D-0007 — Q&A architecture: retrieval-grounded answers via a provider seam
- **Date:** 2026-06-01
- **Context:** Phase 4 needs `ask`/`explain` that are useful but must not hallucinate, must stay local-first/offline, and must be ready for real providers later.
- **Decision:**
  - **Read-only orchestration in `modules/qa.py`:** retrieve → assemble context → generate. No schema change (Q&A reads existing index tables).
  - **Retrieval reuses `index.search`** but with **OR** semantics (new `op` param) plus a stopword filter, because natural-language questions don't co-occur as ANDed tokens. Full chunk text is loaded via `repo.get_chunk_content`.
  - **Grounding contract:** context chunks are delimited, source-tagged, and labeled as *data, not instructions* (prompt-injection posture, SECURITY.md §5). The system prompt instructs the model to answer only from context and to **decline rather than guess**. If retrieval is empty, `qa.answer` returns a decline **without calling the provider**.
  - **Attribution is computed from retrieval** (`RetrievedChunk.location` = `file:start-end`), never from the model, so provenance can't be fabricated.
  - **Provider readiness:** all generation flows through `providers.ai.get_provider()`/`complete(prompt, system=, context=)`. A real Claude/OpenAI/Ollama provider registers in `_REGISTRY` and maps (system/context/prompt) to its API — no caller changes. `MockAIProvider` stays the default (no keys). No stub providers built now (avoid dead code).
- **Rationale:** Ships honest, grounded, offline Q&A immediately; the `Answer`/`SearchHit` types + provider seam mean real models and (D-0006) semantic retrieval drop in without redesign.
- **Status:** Accepted.

## D-0006 — Indexing architecture: line-window chunks + FTS5, with a semantic seam
- **Date:** 2026-06-01
- **Context:** Phase 3 needs working keyword search now, but must not require a redesign when embedding/semantic search is added later.
- **Decision:**
  - **Chunking** is line-based, non-overlapping windows (default 50 lines), 1-based inclusive line ranges (`modules/index.chunk_text`). AST-aware chunking is deferred.
  - **Storage:** `chunks` holds metadata (line range, tags, per-chunk `content_hash`); chunk text lives only in the `chunks_fts` FTS5 table (no duplication). Each chunk carries its own `content_hash` — the future key for caching embeddings without re-chunking.
  - **Incremental reindex** is keyed on a new `files.indexed_hash` (sha256 of the indexed text). Unchanged files are skipped purely on hash equality.
  - **Search** returns a stable `SearchHit` dataclass (`modules/index.search`). Keyword (bm25) search is one strategy; a future `semantic_search` returns the same type, so callers (CLI, Phase 4 Q&A) never change. A future `embeddings(chunk_id, vector, model)` table attaches to `chunks` via `chunk_id`/`content_hash`.
  - **FTS query safety:** free text is tokenized, each token quote-escaped and wrapped, joined with implicit AND — never passed raw to `MATCH`.
- **Rationale:** Ships useful local-first search immediately with stdlib only, while the chunk model + result type form a clean seam for semantic search.
- **Status:** Accepted.

## D-0005 — Stdlib-only runtime for the foundation
- **Date:** 2026-06-01
- **Context:** The foundation must reliably run on a clean machine; network/dep friction is a risk.
- **Decision:** Phase 1 runtime depends only on the Python standard library (argparse, sqlite3, pathlib, json, unittest). Richer libraries (Typer, Rich, pytest, embeddings clients) are adopted deliberately in later phases.
- **Rationale:** Guarantees installability and testability now; keeps the foundation simple and reversible.
- **Status:** Accepted.

## D-0004 — Storage & search: local-first SQLite, FTS5 keyword search first
- **Date:** 2026-06-01
- **Context:** Single power user, daily tool, privacy matters; semantic search is desirable but heavier.
- **Decision:** Use on-device SQLite for all data; implement FTS5 keyword search first, with a design seam for embeddings/semantic search later.
- **Rationale:** Zero recurring cost, private, fast to ship; FTS5 confirmed available (SQLite 3.49.1).
- **Status:** Accepted.

## D-0003 — AI backend: provider abstraction with a mock now
- **Date:** 2026-06-01
- **Context:** AI quality matters but an API-key dependency would block foundation progress.
- **Decision:** Define an `AIProvider` interface and ship a `MockAIProvider` default; wire a real Claude provider later behind the same interface.
- **Rationale:** Whole pipeline becomes testable offline; no key needed yet; provider is swappable.
- **Status:** Accepted.

## D-0002 — Interface: CLI-first
- **Date:** 2026-06-01
- **Context:** Need a usable daily tool quickly; dashboard is the eventual portfolio centerpiece.
- **Decision:** Build the CLI (`devos ...`) first; defer the TypeScript/React dashboard to Phase 7.
- **Rationale:** Fastest path to real daily utility; the core logic the dashboard needs gets built first.
- **Status:** Accepted.

## D-0001 — Stack: Python core + TypeScript/React frontend
- **Date:** 2026-06-01
- **Context:** Need strong AI/code-parsing ecosystem plus an impressive UI eventually.
- **Decision:** Python for the core + CLI; a separate TypeScript/React dashboard added in Phase 7.
- **Rationale:** Python is best for AI/embeddings/tree-sitter; React gives a serious portfolio UI later. CLI-first keeps the two concerns cleanly separated.
- **Status:** Accepted.
