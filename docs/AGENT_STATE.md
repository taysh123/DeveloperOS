# AGENT_STATE — Single Source of Truth

> Read this FIRST every session. It is the authoritative record of where the project
> stands and what to do next. Update it after every meaningful work session.

_Last updated: 2026-06-11_

## Current phase
**v0.6.0 — feature-complete dashboard + first real AI provider.** Phases 0–9 complete. **Dashboard
slices 1–9 shipped:** Home · Tasks · Notes · Search & Ask · Debug · Projects (with **Project Deep
Dive / Study**) · **Learning Center** · **Career** · **Meeting** (summary + action-items→tasks
bridge) · **Settings & AI Management**, plus **CRUD polish**, over a CSRF-token-guarded loopback
API. **Dashboard is at full CLI parity.** The first **real AI provider** shipped: **Ollama**
(local, free, stdlib-only `urllib`, graceful degradation) behind the existing `providers.ai`
seam — default remains the offline mock and the Settings AI toggle is unchanged (no-cost policy).
Also in v0.6.0: **AND-first retrieval** (OR fallback), **secret-aware scanning**
(`SECRET_FILE_PATTERNS`, `skipped_secrets`), and **GitHub Actions CI** (py3.11–3.13, Linux+Windows).
IA = Work · Understand · Grow · System (D-0021…D-0025 + `docs/FUTURE_ROADMAP.md`).

## Current milestone
**Final polish complete (D-0034): real screenshot gallery + v1.0 declared.** Nine genuine
captures (`docs/screenshots/`) made by `tools/take_screenshots.py` (dev-time Playwright driving
the real dashboard through normal flows; native window + installer via Win32 `PrintWindow`).
The pass **found and fixed a shipped bug**: the Meeting tab crashed the SPA on render (string
`style` prop from slice 9 — that slice's smoke was API-only); guarded by
`test_no_string_style_props` + `test_readme_screenshots_exist`. README: gallery + v1.0 status.
TDD **363/363** (+2). **v1.0 declared per the FUTURE_ROADMAP §1 checklist (all Core items
shipped) — D-0034.**

## Previous milestone
**Slice 16 complete (D-0033): native desktop shell via Chromium app-mode window.** `devos app` /
`DeveloperOS.exe` open a **standalone app window** (Edge-first `--app=` mode; Chrome fallback;
default-browser fallback with honest note; `--browser` escape hatch). `_find_app_browser` (App
Paths registry + standard locations, stdlib winreg), `_open_window`, `_open_ui`; D-0030 lifecycle
otherwise unchanged; `index.html` title → "DeveloperOS" (window title). pywebview/WebView2
bindings rejected (runtime dep vs D-0005); Tauri/Electron rejected again. **Zero new runtime/
deps/surface; SECURITY unchanged.** Live-verified: real `msedge --app=` window process for both
the command and the rebuilt exe; installer pipeline rebuilt. TDD **361/361** (+5). **Desktop
ladder complete (A–E).**

## Previous milestone
**Slice 15 complete (D-0032): Windows installer (desktop ladder step D).** Inno Setup per-user
installer (`packaging/installer.iss`, `build_installer.ps1` → `DeveloperOS-Setup-<v>.exe`, ~11 MB;
version from `devos/__init__.py`): `PrivilegesRequired=lowest` → `%LOCALAPPDATA%\Programs\
DeveloperOS`, Start-Menu shortcut + opt-in desktop icon, **KEEP-USER-DATA** uninstall
(`%APPDATA%\DeveloperOS` survives), manual update path via GitHub Releases (no auto-update code,
no new network surface), `LICENSE` (MIT) added. **Live-verified full cycle:** silent install →
installed exe serves dashboard → silent uninstall removes app/shortcut, sentinel user data
survives. **Finding:** PyInstaller onefile parent+child — force-killing only the parent orphans
the server + locks the exe; Ctrl+C stops both (documented in packaging/README + KNOWN_ISSUES).
TDD **356/356** (+5). SECURITY unchanged.

## Previous milestone
**Slice 14 complete (D-0031): PyInstaller packaging foundation (desktop ladder step C).**
`packaging/`: `devos.spec` (onefile, console=True, upx=False; datas = `devos/api/static/**` +
`storage/schema.sql`; hiddenimports = collect_submodules), `launch_devos.py` (exe wraps
`devos app`, args pass through), `build.ps1`, developer README; `tools/make_icons.py` gained a
stdlib `write_ico` → committed multi-size `packaging/devos.ico` (16/32/48/256, PNG entries).
**Real `DeveloperOS.exe` built (~9.6 MB) and smoke-verified** (isolated `DEVOS_HOME`: fresh init
from bundled schema; dashboard + PWA manifest + API served from bundled assets; second exe
invocation reused the instance). PyInstaller = **dev-time only**; runtime stays stdlib-only;
no CI builds (step-D candidate). TDD **351/351** (+4, `tests/test_packaging.py`).

## Previous milestone
**Slice 13 complete (D-0030): `devos app` launcher (desktop ladder step B).** Lifecycle: probe →
reuse-or-start → ready-wait → open → serve (blocking) → Ctrl+C. Read-only `/api/session` probe
identifies a running DeveloperOS (single instance per port); occupied ports detected via an
**exclusive-bind check** (Windows findings: firewall silently drops SYNs to closed loopback ports,
and HTTPServer's SO_REUSEADDR lets a second bind succeed silently — both encoded in tests);
auto-init on first run; friendly plain-language output. No new API surface; SECURITY unchanged.
TDD **347/347** (+7, `tests/test_app_cmd.py`); live smoke: launcher serves, second instance reuses
in ~300 ms.

## Previous milestone
**Slice 12 complete (D-0029): desktop strategy + PWA foundation.** Long-term direction decided —
**PWA front + packaged Python backend** ladder (A: PWA ✅ → B: `devos app` launcher → C: PyInstaller
`devos.exe` → D: Inno Setup installer + optional manual update check → E: Tauri only-if-justified;
**Electron rejected**). Shipped step A: `static/manifest.webmanifest` (standalone, start_url/scope
"/", `#0f1117`, 192/512 + maskable icons + apple-touch), brand mark `>_` generated by stdlib-only
`tools/make_icons.py` (PNGs committed) + `icons/favicon.svg`, index.html head wiring, `.png`/
`.webmanifest` in `_CONTENT_TYPES` (only backend change — two dict entries). **Installable from
Edge/Chrome as a desktop app.** No service worker by design; no new endpoints; SECURITY unchanged.
TDD **340/340** (+6); live smoke verified (manifest type + icons + guarded write 201/403).

## Previous milestone
**Dashboard slice 11 complete (D-0028): onboarding — welcome + live get-started checklist.**
`WelcomeGuide` on Home: privacy/cost stated up front; 6 deep-linking steps (import → search → ask →
learn → tasks/notes → settings) with live done-state — data-backed from `/api/overview` (projects /
task_counts / where_i_left_off.memory), click-backed via localStorage (`devos.onboarding`) for the
read-only surfaces. Always visible while the workspace is empty; dismissible after; resurface link.
`App.go(tabId)` deep links + focuses `#main`. **Zero new endpoints; SECURITY unchanged.** TDD
**334/334** (+6 contract tests); live smoke verified (fresh-home markers + guarded write 201/403).

## Previous milestone
**Dashboard slice 10 complete (D-0027): design system + accessibility pass.** `styles.css` is the
single design source of truth — token scales (spacing/radius/type/motion + semantic colors,
`--focus-ring`), 15px body / 12px floor, button/input/tab min-heights (44px on coarse pointers),
`:active` + 150ms transitions, `prefers-reduced-motion` collapse; dark-only by choice, offline
system fonts. `app.js`: WAI-ARIA tabs (roving tabindex + Arrow/Home/End, `aria-controls` +
`role="tabpanel"`), skip link → focusable `<main>`, `Msg` errors → `role="alert"`, shared `Loading`
primitive, `ConfirmDelete` focus management + Escape, `aria-invalid`/`aria-describedby` wiring.
**No new endpoints/surface; SECURITY unchanged.** Contract pinned by `tests/test_ui_static.py`.
TDD **328/328** (+10); live socket smoke verified (static contract + guarded write 201 + 403).

## Previous milestone
**v0.6.0 cut.** Slice 9 (Meeting tab): `modules/meeting.extract_action_items` (deterministic, never
calls a provider) + `app.py` `meeting_payload` + inline `POST /api/meeting` (transcript NOT
persisted; inherits D-0018 guards); React+htm **Meeting** tab with `ActionItemsBridge` reusing
`POST /api/tasks/create` per selected item (no new write surface). `providers/ollama.py`
(`OllamaProvider`: `complete` + `ping`, env `DEVOS_OLLAMA_URL`/`DEVOS_OLLAMA_MODEL`, labeled
"[OLLAMA UNAVAILABLE]" degradation) registered via `providers/__init__`. `qa.retrieve` AND→OR.
`ingest.is_secret_file` + skip-before-read. TDD **318/318** (+24); live socket smoke verified
(meeting 200 + 403-without-token).

## Next immediate step
**None — the project is complete.** v1.0.0 is released (annotated tag + GitHub release with
Setup/exe assets; final install→launch→uninstall validation passed; repo description/topics
set). Any future session should treat FUTURE_ROADMAP's v2.0 ideas (Safe Action Agent, semantic
search behind D-0006, editor/terminal presence, Plugins UI, cloud providers under a changed
no-cost policy) as **optional, on-request work only** — start with `/plan` as always.

## Tasks
### In progress
- _None. Dashboard slice 4 complete; further dashboard surfaces are on-request only._

### Completed
- [x] Final polish (2026-06-12): screenshot gallery + v1.0 declaration (D-0034). 9 real captures
      via `tools/take_screenshots.py` (dev-time Playwright; PrintWindow for native shots); README
      gallery + v1.0 status; **fixed shipped Meeting-tab SPA crash** (string `style` prop from
      slice 9; API-only smoke missed it) + 2 guard tests. TDD **363/363**. v0.9.0 released
      earlier same day (window-mode assets).
- [x] Slice 16 (2026-06-12): native desktop shell (D-0033). App-mode window (Edge-first
      `--app=`, Chrome fallback, default-browser fallback, `--browser` flag) wired into the
      D-0030 launcher; `index.html` title → "DeveloperOS". pywebview/Tauri/Electron rejected.
      Zero new deps/surface. Live-verified window process for `devos app` + rebuilt exe;
      installer pipeline rebuilt. TDD **361/361** (+5). Desktop ladder complete (A–E).
- [x] Slice 15 (2026-06-11): Windows installer (ladder step D, D-0032). `packaging/installer.iss`
      (per-user, Start-Menu, KEEP-USER-DATA uninstall) + `build_installer.ps1` (version from
      `__init__.py`; ISCC discovery + winget hint) + LICENSE (MIT). Real Setup built (~11 MB);
      full silent install→smoke→uninstall cycle verified incl. user-data survival sentinel.
      PyInstaller parent/child force-kill caveat documented. TDD **356/356** (+5). SECURITY unchanged.
- [x] Slice 14 (2026-06-11): PyInstaller packaging foundation (ladder step C, D-0031).
      `packaging/devos.spec` + `launch_devos.py` (wraps `devos app`) + `build.ps1` + README +
      `devos.ico` (stdlib `write_ico`, 16/32/48/256 PNG entries). Real exe built (~9.6 MB),
      smoke-verified (bundled schema/static; single-instance reuse). Dev-time dep only; no CI
      builds. TDD **351/351** (+4). SECURITY unchanged.
- [x] Slice 13 (2026-06-11): `devos app` launcher (ladder step B, D-0030). `commands/app_cmd.py`:
      probe (read-only `/api/session` token check) → reuse-or-start → `_port_takeable` exclusive
      bind (Windows SO_REUSEADDR/firewall-drop findings) → auto-init → ready-wait thread →
      `webbrowser.open` → blocking serve. `--port`/`--no-browser`. TDD **347/347** (+7); live
      smoke verified (single instance ~300 ms reuse). No new API surface; SECURITY unchanged.
- [x] Slice 12 (2026-06-11): desktop strategy + PWA foundation. D-0029 ladder decided (PWA →
      launcher → PyInstaller exe → installer → Tauri-only-if-justified; Electron rejected).
      Shipped: `manifest.webmanifest` (standalone, 192/512 + maskable), `tools/make_icons.py`
      (stdlib PNG writer; committed icons + favicon.svg), index.html head wiring, `.png`/
      `.webmanifest` content types. Installable from Edge/Chrome. No SW; no new endpoints;
      SECURITY unchanged. TDD **340/340** (+6); live smoke verified.
- [x] Dashboard slice 11 (2026-06-11): onboarding. `WelcomeGuide` on Home (privacy/cost up front;
      6 deep-linking steps with live done-state: data-backed from `/api/overview`, click-backed via
      localStorage `devos.onboarding`); always-on while workspace empty, dismissible after, resurface
      link; `App.go(tabId)` + focus `#main`. Zero new endpoints; SECURITY unchanged. Token CSS
      (`.welcome`/`.checklist`). TDD **334/334** (+6); live smoke verified. D-0028.
- [x] Dashboard slice 10 (2026-06-11): design system + a11y pass. `styles.css` token scales
      (spacing/radius/type/motion/semantic + `--focus-ring`; 15px body, 12px floor; min-heights +
      `:active` + 150ms transitions; `prefers-reduced-motion`; dark-only, offline system fonts).
      `app.js`: WAI-ARIA tabs (roving tabindex + arrows), skip link + focusable `<main>` + `<footer>`,
      `Msg` alert/status split, `Loading` primitive, `ConfirmDelete` focus+Escape, `aria-hidden`
      glyphs, `aria-invalid`/`aria-describedby`. No new endpoints; SECURITY unchanged. New
      `tests/test_ui_static.py` pins the contract. TDD **328/328** (+10); live smoke verified. D-0027.
- [x] v0.6.0 (2026-06-11): Meeting tab (slice 9) + Ollama provider + AND-first retrieval + secret-aware
      scan + CI. Built TDD in a TEMP working copy and merged into this repo (19 files; SHA-256
      tree-comparison verified strict superset — no loss). Deterministic `meeting.extract_action_items`
      + inline `POST /api/meeting` (transcript not persisted) + action-items→tasks bridge (reuses
      `tasks/create`, no new write surface); `providers/ollama.py` (local/keyless/"[OLLAMA UNAVAILABLE]"
      degradation; mock stays default); `qa.retrieve` AND→OR; `ingest.SECRET_FILE_PATTERNS` +
      `skipped_secrets` (skip-before-read); `.github/workflows/ci.yml`. Version → 0.6.0. CI exposed a
      latent Windows-8.3-short-path bug in `repo.find_project_for_path` (abspath→realpath fix + repro
      test). TDD **318/318** (+24); live socket smoke verified. D-0026; SECURITY §1/§2/§5/§8/§9;
      tagged `v0.6.0`.
- [x] Dashboard slice 8 (2026-06-03): Career tab. `app.py` `jobs_payload`/`interview_payload`/`cv_payload`
      (+ `create_job_action`/`update_job_action`/`delete_job_action`, `_clean_optional`); `GET /api/jobs`
      + `GET /api/jobs/interview` + `POST /api/jobs/{create,update,delete}` + inline `POST /api/cv`.
      Reuse `repo` job CRUD + `repo.JOB_STATUSES` + `career.analyze_cv`/`interview_prep`. React+htm
      **Career** tab (AddJob/JobRow with inline status+edit+ConfirmDelete; InterviewPrep; CvCheck with
      coverage% + matched/missing chips). **CV text not persisted**; no schema/`server.py` change. TDD
      **294/294** (+22); live smoke verified (CRUD + interview + CV + 403). D-0025; SECURITY §5/§9/§8.
- [x] Dashboard slice 7 (2026-06-02): CRUD polish. `repo.delete_project` (cascade via FKs + `reconcile_fts`;
      index-only, no disk deletion). `app.py` `delete_task_action`/`delete_note_action`/`delete_project_action`
      (+ `_require_id`) in `_POST_ACTIONS`; reuse `repo.delete_task`/`delete_memory`. React+htm: reusable
      `ConfirmDelete` (two-step) on task/note rows; inline task-title edit; project pickers on add-task/
      add-note; `ProjectDetail` **danger zone** with type-to-confirm project delete. Small danger CSS. No
      `server.py`/schema change. TDD **272/272** (+12); live smoke verified (cascade + 403). D-0024; SECURITY §8.
- [x] Dashboard slice 6 (2026-06-02): Learning Center. `app.py` `learn_payload`/`quiz_payload`/
      `exercise_payload`/`grade_payload` (+ shared `_chunk_sources`) reusing `modules/learning`;
      `GET /api/learn|quiz|exercise` (target required; level validated; `n` clamped 20/10) +
      inline `POST /api/grade` (multi-line answer; inherits D-0018 guards). React+htm **Learn** tab
      (target/project/depth + Explain/Quiz/Exercises + grade box; shared `AnswerBlock`); no new CSS.
      Read-only/grounded; declines when unindexed. TDD **260/260** (+13); live smoke verified. D-0023; SECURITY §5/§8.
- [x] Dashboard slice 5 (2026-06-02): Settings & AI Management. New `devos/settings.py` (non-secret
      `settings.json` store + provider catalog mock/ollama/claude/openai with privacy/cost metadata;
      `effective_provider_name` → offline mock when disabled/unavailable; `key_present` boolean only).
      Config/Workspace resolve provider env→settings→mock + `ai_enabled` (backward compatible). `app.py`
      `system_payload`/`settings_payload`/`update_settings_action` + `GET /api/system`, `GET /api/settings`,
      inline `POST /api/settings` (whitelists `ai_enabled`/`ai_provider`; inherits D-0018 CSRF/Origin/JSON/
      size guards). React+htm **Settings** tab (System status + AI settings + prepared provider-config).
      Version 0.1.0→0.5.0. **No keys in SQLite/JSON/frontend** (env-var/keychain; presence boolean). TDD;
      **247/247** (+20); live socket smoke verified (no key leak). D-0022; SECURITY §2/§8; FUTURE_ROADMAP.
- [x] Dashboard slice 4 (2026-06-02): Project Deep Dive / Study. `app.py` `study_payload` + read-only
      `GET /api/projects/study` (reuses `qa.explain`+`learning.quiz`+`repo.top_files`/`category_breakdown`
      + deterministic `interview_prep`; id-validated, `n` clamped; no new engine). React+htm `ProjectStudy`
      (Start here/Key files/How this works/Questions/Interview prep + project-scoped Ask) from project
      detail. TDD; **227/227** (+5); live smoke verified. D-0021 (+ long-term roadmap); SECURITY §8.
- [x] Dashboard slice 3 (2026-06-02): Debug tab. `app.py` `debug_payload` + read-only `POST /api/debug`
      (inline in `route()`, reuses `debug.diagnose`, inherits slice-1 CSRF; trace=data, index-only, not
      persisted). React+htm Debug tab (paste → Analyze → result cards). TDD; **222/222** (+6); live smoke
      verified (high-confidence diagnosis w/ sources). D-0020; SECURITY §5 + §8.
- [x] Dashboard slice 2 (2026-06-02): Projects tab. `app.py` `project_detail` + GET
      `/api/projects/detail` + POST `/api/projects/scan` (validate path → `ingest.scan_project` →
      `index_mod.index_project`; in `_POST_ACTIONS`, inherits slice-1 CSRF guards). React+htm
      Projects tab (list/detail/import) with confirm-before-write `ScanFlow` + Re-scan. TDD;
      **216/216 tests** (+8); live smoke verified. D-0019; SECURITY §8 + posture row; KNOWN_ISSUES updated.
- [x] Dashboard action slice 1 (2026-06-02): action-oriented, tabbed dashboard. `repo.update_memory`;
      `app.route` extended (keyword-only `method`/`body`) with POST `tasks/notes create|update` (reuse
      repo writes) + GET `search`/`ask`/`explain` (reuse `index`/`qa`, `ws.ai`); `server.py` `do_POST`
      + `/api/session` with CSRF token + Origin allowlist + JSON-only + 64 KB cap, no CORS; React+htm
      SPA rebuilt with tabs (Home/Tasks/Notes/Search&Ask), token-aware `post()`, accessible labels.
      TDD; **208/208 tests pass** (+25); live smoke verified end-to-end. D-0018; SECURITY §8 NOW.
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
- [x] Phase 5: Debug Assistant — `modules/trace` (pluggable Python/Node/generic parsers) +
      `modules/debug` (`diagnose`: index-only frame location, reuses `qa.retrieve`/`assemble_context`
      + `providers/ai`, structured grounded `DebugDiagnosis` w/ confidence; declines without calling
      the provider when no evidence); `repo.find_file_by_path`; exposed `qa.resolve_project`;
      `devos debug` (arg/--file/stdin). 17 new tests (83 total) pass; dogfooded (located real file,
      high confidence; security: no filesystem read from trace paths). D-0008 + SECURITY §5 updated.
- [x] Phase 6: Task Manager & Memory — schema **v3** (`tasks.priority`) + migration; `storage/repo`
      task + memory CRUD/search (idempotent memory create); `modules/recall` (retrieval-only:
      memory + tasks via LIKE + code via `qa.retrieve`); `devos task` (add/list/show/set/rm),
      `devos remember`, `devos recall`. 18 new tests (103 total) pass; dogfooded (task lifecycle,
      remember, recall grouping tasks+code; status shows counts). D-0009 logged.
- [x] Phase 7: Dashboard & Polish — `devos/api` stdlib `http.server` (loopback, read-only): `app.py`
      data builders + `route()` (JSON `/api/overview|projects|tasks|memory|recall` + static, traversal-safe)
      reusing `repo`/`modules.recall`; `server.py` wrapper; **React+htm SPA** vendored offline in
      `static/` (`devos serve`). 12 new tests (115 total) pass; dogfooded live (overview/index/static
      served on 127.0.0.1:8765). D-0010 + SECURITY §8 updated. Mock provider unchanged.
- [x] Phase 8: Documentation Automation — `modules/docgen` (`generate` for readme/architecture/api/
      setup via `qa.retrieve`+project facts, and changelog/decisions/milestone via memory/tasks incl.
      global records); declines (no provider call) when ungrounded; `devos docgen <type>` (stdout
      default, `--output` no-clobber/`--force`); added `repo` `include_global`. 11 new tests (126
      total) pass; dogfooded (grounded readme/decisions, no-clobber). D-0011 + SECURITY §4/§5 noted.
- [x] Phase 9 slice 1: Learning Assistant — `modules/learning` (`learn` → `Lesson`: file mode via
      repo helpers, topic mode via `qa.retrieve`, leveled eli5/intermediate/advanced prompts,
      declines when ungrounded); `devos learn <path|topic> [--level]` (reuses `ask_cmd.print_answer`).
      7 new tests (133 total) pass; dogfooded (file + topic grounding, leveled, sources). D-0012.
- [x] Phase 9 slice 2: Learning Quiz — `learning.quiz` → `Quiz` (n grounded questions, default 5
      clamped [1,20], file/topic mode via shared `_resolve_chunks`, declines when ungrounded);
      `devos quiz <path|topic> [--n N]`. 7 new tests (140 total) pass; dogfooded (file/topic + reject n<1). D-0013.
- [x] Phase 9 slice 6: Meeting/Transcript foundation — `modules/meeting.summarize` (grounded
      summary/decisions/action-items, declines on empty, 12k char cap) + `devos meeting summarize <file>`
      (utf-8-sig read). Cross-cutting: console-safe UTF-8 stdout in `cli.main`. 7 new tests (183 total)
      pass; dogfooded live. D-0017.
- [x] Phase 9 slice 5: Plugin/Extension seam — `providers.ai.register_provider`; `devos/plugins.py`
      (entry-point group `devos.plugins` + opt-in local `<data_dir>/plugins/*.py` via
      `DEVOS_ENABLE_LOCAL_PLUGINS=1`; fail-safe `LOADED`/`ERRORS`; `ensure_loaded` at CLI startup);
      `devos plugins`. 8 new tests (176 total) pass; dogfooded (gating off→on, plugin command runs).
      D-0016 + SECURITY new code-exec/supply-chain note.
- [x] Phase 9 slice 4: Career Assistant (slice 1) — schema **v4** (`job_leads`) + migration;
      `repo` job CRUD; `modules/career` (`analyze_cv` deterministic keyword match via `qa.question_terms`;
      `interview_prep` grounded on job notes, declines when noteless); `devos job` (add/list/show/set/rm),
      `devos cv <file> [--job]` (notes-only target), `devos interview <id>`. 16 new tests (167 total) pass;
      dogfooded (job lifecycle, cv coverage, interview prep, status shows job_leads). D-0015.
- [x] Phase 9 slice 3: Exercises & Grading — `learning.exercise` → `Exercise` (n grounded tasks,
      default 3 clamped [1,10]) and `learning.grade` → `Grade` (evaluates a supplied answer vs
      retrieved code; Feedback/Strengths/Weaknesses + file:line; stateless/read-only; decline when
      ungrounded; empty answer → ValueError); `devos exercise` + `devos grade` (`--answer`/`--answer-file`).
      11 new tests (151 total) pass; dogfooded. D-0014.

### Blocked
- _None._

## Known assumptions
- Single power user; multi-user is a future extension.
- Foundation runtime is stdlib-only (no external pip deps required to run).
- AI is mocked **by default** (no API key needed). As of v0.6.0 a real local **Ollama** provider is
  available — opt-in via the Settings tab, keyless, free, nothing leaves the machine. Selecting a
  still-unwired cloud provider (claude/openai) keeps the **effective** provider on the offline mock;
  cloud providers stay unwired by deliberate no-cost policy.
- Windows is the primary dev OS (paths handled cross-platform via `pathlib`).

## Open decisions
- CLI framework: stdlib `argparse` now; revisit Typer/Rich in Phase 7. _(Default chosen.)_
- Semantic-search *architecture* decided (D-0006: `SearchHit` seam + per-chunk hash). The
  embeddings *backend* (which local model/library) remains open and deferred to a later phase.

## Working context
- Repo: `C:\Projects\DeveloperOS` · git branch: `main` · platform: Windows 11 · Python 3.13.5.
- Remote: `origin` = https://github.com/taysh123/DeveloperOS (branch + PR workflow; CI on push/PR).
- Run app: `pip install -e .` then `devos <command>`. Tests: `python -m unittest discover -s tests`.
- Isolate the data dir in dev/tests via the `DEVOS_HOME` env var.

## How to continue (session startup)
1. Read this file. 2. Read ROADMAP.md. 3. Read TODO.md. 4. Read latest PROGRESS_LOG.md entry.
5. Read DECISIONS.md / KNOWN_ISSUES.md if relevant. 6. Resume from "Next immediate step".
