# DeveloperOS — Decision Log

_Architectural & product decisions, newest first. Each: context · decision · rationale · status._

---

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
