# DeveloperOS — Known Issues

_Active issues, limitations, and tech debt. Resolved items move to PROGRESS_LOG/CHANGELOG._

## Limitations (by design, for now)
- **AI is mocked.** Q&A/debug/docgen will return clearly-labeled stub output until a real
  Claude provider is wired in (Phase 4+). No API key is required yet.
- **Keyword search only.** Semantic/embedding search is deferred to a later phase (D-0004).
- **No dashboard yet.** CLI is the only interface until Phase 7.

## Open issues
- _None recorded yet._

## Tech debt watchlist
- CLI uses stdlib `argparse`; revisit Typer/Rich for UX in Phase 7 (D-0005).
- Migration runner is intentionally minimal; revisit if schema churn grows.
