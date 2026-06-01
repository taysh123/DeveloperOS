# DeveloperOS — Project Brief

_Last updated: 2026-06-01_

## What it is
**DeveloperOS** is an AI-powered personal operating system for developers. It is
one coherent system — not a scattered set of tools — with a strong core that helps
a developer understand any software project deeply, debug it, track work on it,
remember decisions about it, and search across everything related to it.

## Who it's for
The **single power user** (the owner/developer) first. Multi-user, cloud sync, and
collaboration are explicit *future* extensions, not early priorities.

## Why it exists
Two goals, held at once:
1. A **real daily productivity tool** the owner actively uses.
2. A **portfolio-grade project** that reads as serious and impressive on a resume.

## What "good" looks like
Useful in daily work · clear and intuitive · technically serious · well organized ·
safe and maintainable · impressive for a portfolio · robust across many iterations.

## Core modules (the product surface)
1. **Project Brain** — scan a repo, identify frontend/backend/db/APIs/auth/tests/configs, map it, explain it in plain language.
2. **Code Map / Code Intelligence** — searchable code index, smart chunking/tagging, dependency & flow detection, module summaries.
3. **Debug Assistant** — ingest errors/stack traces/logs, find root causes & relevant files, explain, propose fixes + verification.
4. **Project Manager** — tasks/bugs/features with status (todo/in-progress/blocked/done), milestones, notes.
5. **Memory Engine** — store decisions, summaries, context; remember across sessions; keep it compact and structured.
6. **Search / Recall** — keyword + semantic search across code, memory, docs, tasks, notes.
7. **Documentation Generator** — READMEs, architecture docs, API docs, setup, changelog, decision logs, milestone summaries.
8. **Safe Action Agent** — suggest/apply code changes, branches/commits/PR summaries, run tests/builds — never destructive silently.
9. **Git Intelligence** — understand commits/diffs, summarize changes, detect risk, connect bugs to commits, spot regressions.
10. **Terminal / Dev Automation** — run the minimum necessary commands (install/test/build/lint/inspect).
11. **Dashboard** — home/overview: active projects, task status, recent updates, blocked items, "where I left off".
12. **Learning Assistant** — explain code at multiple levels, teach concepts, generate exercises/quizzes (future phase).
13. **Career Assistant** — track job leads, analyze CVs, suggest keywords, interview prep (future phase).
14. **Future Extensions** — meeting assistant, transcript summarizer, multi-user, cloud sync, browser/VS Code integration, plugins, multi-agent.

## Foundational decisions (see DECISIONS.md for rationale)
- **Stack:** Python core + CLI first; TypeScript/React dashboard deferred to Phase 7.
- **Interface:** CLI-first (`devos ...`).
- **AI:** Provider abstraction with a **mock** implementation now; real Claude provider drops in later behind the same interface.
- **Storage/Search:** Local-first SQLite; FTS5 keyword search first, embeddings/semantic search later.
- **Runtime deps:** stdlib-only for the foundation, to guarantee it runs anywhere; richer libs adopted deliberately in later phases.

## Operating principles
Understand before building · maintain a single source of truth (`AGENT_STATE.md`) ·
never duplicate work · small safe incremental changes · document assumptions ·
keep the architecture open for future modules · clarity over cleverness.
