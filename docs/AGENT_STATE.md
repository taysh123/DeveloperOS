# AGENT_STATE — Single Source of Truth

> Read this FIRST every session. It is the authoritative record of where the project
> stands and what to do next. Update it after every meaningful work session.

_Last updated: 2026-06-02_

## Current phase
**Post-roadmap extensions (on-request).** Phases 0–9 complete. **Dashboard slices 1–7 shipped:**
Home · Tasks · Notes · Search & Ask · Debug · Projects (with **Project Deep Dive / Study**) · **Settings
& AI Management** · **Learning Center**, plus **CRUD polish** (deletes + project pickers + inline edit),
over a CSRF-token-guarded loopback API. Slices 1–6 merged to `main` (PRs #1–#5); slice 7 on branch
`feat/dashboard-crud-polish` (PR pending). The **long-term dashboard roadmap** is recorded
(D-0021…D-0024 + `docs/FUTURE_ROADMAP.md`): IA = Work · Understand · Grow · System. **Project is at v0.5.0.**

## Current milestone
**Dashboard slice 7 complete (D-0024).** CRUD polish: delete tasks/notes (two-step confirm) and projects
(**type-to-confirm**, **index-only — never deletes disk files**); project pickers on the add-task/add-note
forms; inline task-title editing. New `repo.delete_project` (cascade via existing `ON DELETE CASCADE` FKs
+ `reconcile_fts`); `POST /api/{tasks,notes,projects}/delete` in `_POST_ACTIONS` (id-validated → 400,
unknown → 404), reusing `repo.delete_task`/`delete_memory`. Inherits D-0018 guards; no `server.py`/schema
change. TDD **272/272** (+12); live socket smoke verified (full flow incl. project cascade + token guard).

## Next immediate step
Open a PR for `feat/dashboard-crud-polish` and merge to `main`. Per the recorded roadmap, the next
highest-leverage slice is the **Career tab** (`modules/career`: job leads / CV match / interview prep),
then the **Meeting Summary tab** (`modules/meeting`), Plugins/Extensions UI, and a design-system/a11y
pass. **Recommend tagging `v0.5.0`** once slices 6–7 are merged to `main` (do not tag before the PRs merge).

## Tasks
### In progress
- _None. Dashboard slice 4 complete; further dashboard surfaces are on-request only._

### Completed
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
- AI is mocked until a real provider is wired in (no API key needed). The dashboard Settings tab lets
  users toggle AI and *select* a provider (mock/ollama/claude/openai), but selection only stores a
  preference — the **effective** provider stays the offline mock until real integrations ship (slice 5).
- Windows is the primary dev OS (paths handled cross-platform via `pathlib`).

## Open decisions
- CLI framework: stdlib `argparse` now; revisit Typer/Rich in Phase 7. _(Default chosen.)_
- Semantic-search *architecture* decided (D-0006: `SearchHit` seam + per-chunk hash). The
  embeddings *backend* (which local model/library) remains open and deferred to a later phase.

## Working context
- Repo: `C:\Projects\DeveloperOS` · git branch: `main` · platform: Windows 11 · Python 3.13.5.
- No remote configured yet.
- Run app: `pip install -e .` then `devos <command>`. Tests: `python -m unittest discover -s tests`.
- Isolate the data dir in dev/tests via the `DEVOS_HOME` env var.

## How to continue (session startup)
1. Read this file. 2. Read ROADMAP.md. 3. Read TODO.md. 4. Read latest PROGRESS_LOG.md entry.
5. Read DECISIONS.md / KNOWN_ISSUES.md if relevant. 6. Resume from "Next immediate step".
