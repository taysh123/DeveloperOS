# DeveloperOS — Known Issues

_Active issues, limitations, and tech debt. Resolved items move to PROGRESS_LOG/CHANGELOG._

## Limitations (by design, for now)
- **AI is mocked.** Q&A/debug/docgen will return clearly-labeled stub output until a real
  Claude provider is wired in (Phase 4+). No API key is required yet.
- **Keyword search only.** Semantic/embedding search is deferred to a later phase; the
  architecture seam is in place (D-0004, D-0006), the embedding backend is not.
- **Chunking is line-based, not AST-aware.** Fixed line windows (default 50) can split
  functions/classes across chunks. AST-aware chunking is a later refinement (D-0006).
- **No dashboard yet.** CLI is the only interface until Phase 7.
- **Q&A answer text is a stub.** With the default mock provider, `ask`/`explain` echo the
  assembled context/prompt (clearly labeled `[MOCK AI]`); real prose arrives when a live
  provider is configured. Retrieval, grounding, and `file:line` citations are real now.
- **Retrieval is keyword (OR) + bm25, not semantic.** It declines only when *no* query term
  matches anywhere; a single incidental token match yields context, leaving semantic
  sufficiency to the model (instructed to decline if context is inadequate). Quality improves
  with semantic search (D-0006) and a real provider (D-0007). Line-window chunks can also
  split a function across chunks, affecting answer completeness.
- **Debug parsing covers Python, Node/JS, and a generic `path:line` fallback only.** Other
  languages fall back to the generic scanner (file:line extraction without error typing). Add
  a parser to `trace.TRACE_PARSERS` to extend (D-0008).
- **Debug analysis prose is a mock stub** until a real provider is configured; evidence,
  index-only file location, citations, and confidence are real now. As with Q&A, debug rarely
  hits the pure "no evidence" decline when the error message contains common words (OR
  retrieval matches incidentally) — but `confidence` and the evidence list still report
  honestly whether any trace files were located in the index.

## Open issues
- _None recorded yet._

## Tech debt watchlist
- CLI uses stdlib `argparse`; revisit Typer/Rich for UX in Phase 7 (D-0005).
- Migration runner is intentionally minimal; revisit if schema churn grows.
- **Ingest `.gitignore` support is a subset:** only the top-level `.gitignore` is read,
  with no negation (`!`), no nested ignore files, and simple `fnmatch` semantics. Refine
  if false-ignores show up on real repos.
- **File classification is heuristic** (extension + path/filename markers). Expect
  occasional miscategorization (e.g. shared `.js`/`.ts` between frontend/backend); revisit
  with AST/content signals in later phases.
