# DeveloperOS — Decision Log

_Architectural & product decisions, newest first. Each: context · decision · rationale · status._

---

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
