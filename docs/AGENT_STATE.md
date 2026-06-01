# AGENT_STATE — Single Source of Truth

> Read this FIRST every session. It is the authoritative record of where the project
> stands and what to do next. Update it after every meaningful work session.

_Last updated: 2026-06-01_

## Current phase
**Phase 9 — Future Modules:** all originally-enumerated directions shipped — **Learning (s1–3),
Career slice 1 (s4), Plugin seam (s5), Meeting foundation (s6).** Phases 0–9 complete.

## Current milestone
**Roadmap Phases 0–9 have all shipped their planned scope.** No approved work pending. Future
extensions (audio STT, action-item→tasks, plugin sandboxing/signing, CV rewrite, real AI
providers, multi-user/cloud) are optional and require an explicit new request + `/plan`.

## Next immediate step
Nothing pending. Awaiting the owner's direction for any future extension (each would start
with a fresh `/plan`). Real AI provider can be wired behind `providers.ai` when desired.

## Tasks
### In progress
- _None. All roadmap phases (0–9) complete; future extensions are on-request only._

### Completed
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
- AI is mocked until a real Claude provider is wired in (no API key needed yet).
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
