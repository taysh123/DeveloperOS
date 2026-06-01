# DeveloperOS — Roadmap

_Last updated: 2026-06-01_

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

## Phase 3 — Code Indexing & Search 🚧 (next)
- **Goal:** A searchable index of code & docs.
- **Scope:** Chunking strategy (line/AST-aware later), tagging, FTS5 index, keyword search; design seam for embeddings/semantic search.
- **Deliverables:** `devos index`, `devos search <query>` (keyword), ranked results with file:line.
- **Completion criteria:** Search returns relevant results on a real repo; reindex is incremental.
- **Risks:** Index bloat; stale index. **Mitigation:** content hashing, incremental updates.
- **Dependencies:** Phase 2.

## Phase 4 — Q&A & Project Understanding ⬜
- **Goal:** Answer "how does X work?" / "where is the auth flow?" with citations.
- **Scope:** Retrieval over the index → context assembly → AI provider; plain-language project explanation; module summaries.
- **Deliverables:** `devos ask "<question>"`, `devos explain [path]`, answers cite files.
- **Completion criteria:** Useful, grounded answers with file references (mock provider returns structured stub; real provider pluggable).
- **Risks:** Hallucination; context limits. **Mitigation:** retrieval-grounded prompts, citations, chunk budgets.
- **Dependencies:** Phase 3.

## Phase 5 — Debug Assistant ⬜
- **Goal:** Turn an error/stack trace/log into root-cause + fix proposal.
- **Scope:** Parse traces, locate referenced files/lines, assemble context, propose cause/fix/verification; optional patch suggestion (no silent writes).
- **Deliverables:** `devos debug` (paste/pipe a trace), structured diagnosis output.
- **Completion criteria:** Correctly locates files from a real trace and produces a coherent diagnosis.
- **Risks:** Trace format variety. **Mitigation:** pluggable parsers per language.
- **Dependencies:** Phase 3 (index), Phase 4 (AI plumbing).

## Phase 6 — Task Manager & Memory ⬜
- **Goal:** Track work and remember decisions across sessions.
- **Scope:** Tasks/bugs/features CRUD with status & milestones; memory store for decisions/summaries/preferences; link memory ↔ project/files; recall surfaced in search.
- **Deliverables:** `devos task ...`, `devos remember ...`, `devos recall ...`.
- **Completion criteria:** Tasks persist with status transitions; memories are searchable and recalled in Q&A.
- **Risks:** Memory sprawl. **Mitigation:** structured, deduped, compact entries.
- **Dependencies:** Phase 1 (storage); integrates with Phases 3–4.

## Phase 7 — Dashboard & Polish ⬜
- **Goal:** Visual overview + UX polish (the portfolio centerpiece).
- **Scope:** TypeScript/React (Next.js) dashboard over a local API exposing projects, tasks, recent activity, blocked items, "where I left off"; CLI UX polish (Rich/Typer adoption considered here).
- **Deliverables:** Local API, dashboard app, screenshots.
- **Completion criteria:** Dashboard reflects live DB state; clean, intuitive home screen.
- **Risks:** Scope creep on UI. **Mitigation:** design pass via `ui-ux-pro-max`; ship MVP first.
- **Dependencies:** Phases 2–6 (data to display).

## Phase 8 — Documentation Automation ⬜
- **Goal:** Generate docs from the indexed project.
- **Scope:** README / architecture / API / setup / changelog / decision-log / milestone-summary generators using retrieval + AI.
- **Deliverables:** `devos docgen <type>`.
- **Completion criteria:** Generated docs are accurate and useful on a real repo.
- **Risks:** Accuracy. **Mitigation:** grounded generation + human review step.
- **Dependencies:** Phases 3–4.

## Phase 9 — Future Modules ⬜
- **Goal:** Career & Learning assistants; extension seams.
- **Scope:** Learning (explain levels, exercises, quizzes), Career (job leads, CV analysis, interview prep), plus seams for meeting assistant, multi-user, cloud sync, browser/VS Code integration, plugins, multi-agent.
- **Deliverables:** TBD per module when reached.
- **Completion criteria:** Core stable first; each module shipped behind the existing architecture.
- **Risks:** Distraction from core. **Mitigation:** do not start until Phases 1–7 are stable.
- **Dependencies:** Stable core.

---

### Cross-cutting concerns (every phase)
Safe Action Agent (no destructive ops without explicit confirmation), Git Intelligence,
Terminal automation (minimum necessary commands), tests, and synchronized docs/state.
