# Plan — Dashboard Slice 5: Settings & AI Management

_Date: 2026-06-02 · Roadmap position: post-Phase-9, Dashboard slices 1–4 shipped → this is **slice 5**._

## Roadmap continuity (where we sit)

- **Phases 0–9:** ✅ complete.
- **Dashboard slices 1–4:** ✅ shipped & merged to `main` (Home/Tasks/Notes/Search&Ask · Debug · Projects · Project Deep Dive/Study), behind the CSRF-token + Origin + JSON + 64 KB loopback guards (D-0018…D-0021).
- **Recorded next priority (D-0021 / AGENT_STATE):** *Settings + AI-provider toggle* — reuse the existing `get_provider(config.ai_provider)` / `ws.ai` seam; keys from env/keychain only; mock default. **This plan implements exactly that.** No parallel roadmap.

This is two deliverables:
- **Part A — `docs/FUTURE_ROADMAP.md`** (product planning only; nothing built).
- **Part B — Dashboard Slice 5: Settings & AI Management** (implemented, TDD).

---

## Part A — `docs/FUTURE_ROADMAP.md` (new, planning only)

Author as Lead Architect + Product Manager. Sections: Vision v1.0 / v2.0; Dashboard, AI, Productivity, Learning, Career, Enterprise roadmaps; Stretch goals; Ideas backlog. Every idea tagged **Core Product / High Value / Nice To Have / Future Research**. No code, no implementation. Cross-links to ROADMAP.md so it extends rather than forks the roadmap.

---

## Part B — Settings & AI Management

### Design decision (the crux): where settings live

- **Non-secret preferences** (`ai_enabled: bool`, `ai_provider: str`) persist in a small JSON file: `<data_dir>/settings.json`. **No schema migration**, data dir is already git-ignored.
- **Secrets (API keys) are never stored** — not in SQLite, not in settings.json, not transmitted to the server. They come from **environment variables** (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) per SECURITY §2. The UI only ever shows a **boolean "detected / not set"**, computed server-side from `os.environ` — never the value.
- **Reuse, don't fork:** keep the single `providers/ai.get_provider()` registry. Only `mock` is registered today, so selecting `claude`/`openai`/`ollama` stores a *preference* but resolves safely to the offline **mock** until a real provider is wired in — the UI states this plainly. No external requests, no key required (mock + offline + free stays the default).

### New module: `devos/settings.py` (standalone, takes `data_dir`)

- `PROVIDERS`: ordered catalog metadata driving the UX (privacy + cost):
  `mock` (local/free/no-key, default), `ollama` (local/free/no-key, endpoint hint), `claude` (cloud/paid/`ANTHROPIC_API_KEY`), `openai` (cloud/paid/`OPENAI_API_KEY`).
- `Settings` dataclass: `ai_enabled`, `ai_provider`.
- `load(data_dir) -> Settings`: read `settings.json`; missing/corrupt → safe defaults (`enabled=True`, `mock`). Ignores any unknown/secret keys.
- `save(data_dir, *, ai_enabled=None, ai_provider=None) -> Settings`: validate provider ∈ catalog ids (else `ValueError`); atomic write; **whitelist only the two keys** (a posted `api_key`/`endpoint` is silently dropped, never written).
- `effective_provider_name(preferred, enabled) -> str`: `enabled and preferred in available_providers()` → `preferred`, else `"mock"`.
- `key_present(provider_id) -> bool`: `bool(os.environ.get(key_env))`; returns only the boolean.

### Config / Workspace integration (minimal, backward-compatible)

- `config.load_config()`: provider resolution becomes `DEVOS_AI_PROVIDER` env (explicit override) → `settings.load(data_dir).ai_provider` → `"mock"`; add `ai_enabled` to `Config`.
- `Workspace.ai`: resolve through `settings.effective_provider_name(...)` so an unavailable/disabled selection falls back to mock (never raises). Defaults keep `ws.ai == mock` → **all existing tests stay green.**

### API (`devos/api/app.py`)

- `system_payload(conn, ws)` → `GET /api/system`: `local_first: True`, `offline: True`, `ai_enabled`, `provider_selected`, `provider_effective`, `version` (`devos.__version__`), `roadmap_phase`, `indexed_project_count`, `dashboard_maturity`, `providers` (catalog + `available`).
- `settings_payload(ws)` → `GET /api/settings`: current `ai_enabled`/`ai_provider` + provider catalog each with `available` and `key_present` (boolean only — no values).
- `POST /api/settings` `{ai_enabled?, ai_provider?}`: handled **inline in `route()`'s POST branch** (like `/api/debug`) since it needs `ws`/`data_dir` not `conn`. Validates provider → friendly 400; persists via `settings.save`; returns the new `settings_payload`. **Drops any `api_key`/`endpoint` fields.** Inherits the D-0018 CSRF + Origin + JSON + 64 KB guards (no `server.py` change).

### Frontend (`devos/api/static/app.js` + `styles.css`)

- New **Settings** tab (IA group "System"): `Home · Tasks · Notes · Search & Ask · Debug · Projects · Settings`.
- **System status** card grid: Local-first ✓ · Offline ✓ · AI On/Off · Provider (effective) · Version · Roadmap phase · Projects indexed · Dashboard maturity.
- **AI settings**: Enable-AI toggle + provider radio list with **privacy** (Local/Cloud) and **cost** (Free/Paid) badges; Save → `POST /api/settings` → confirmation. When a cloud provider is selected: clear note "Not available yet — still running the offline mock, so nothing leaves your machine."
- **Provider details (prepared, honest)**: API-key / endpoint / model fields rendered **disabled** with helper text ("Keys come from environment variables like `ANTHROPIC_API_KEY` — DeveloperOS never stores them"); show **Detected / Not set** for the selected cloud provider's key. These fields are **not** transmitted.

### Version

Bump `0.1.0 → 0.5.0` in `devos/__init__.py` + `pyproject.toml` (reflects 5 shipped dashboard slices; surfaced in System status and `devos --version`).

### TDD (write tests first)

- **`tests/test_settings.py`** (new): defaults when no file; save+reload roundtrip; invalid provider → `ValueError`; corrupt JSON → defaults; **`save` ignores/strips `api_key`** (security); `effective_provider_name` (disabled→mock, unknown→mock, known→itself); `key_present` reads env as boolean.
- **`tests/test_api.py`** (extend): `GET /api/system` shape + `version`/`indexed_project_count`; `GET /api/settings` lists providers + `key_present` booleans (never a value); `POST /api/settings` updates provider+enabled and persists; invalid provider → 400; **POST with `api_key` does not persist it**; live-server `POST /api/settings` without token → 403.

### Verification (verification-before-completion)

- `python -m unittest discover -s tests` — full suite green (expect ~227 + new).
- Live smoke: `devos serve`, open Settings, toggle AI, switch provider, confirm persisted across reload; confirm key value never appears in any payload; `devos --version` shows 0.5.0.

### Docs to synchronize (after green)

ROADMAP (slice 5 entry), AGENT_STATE, TODO, PROGRESS_LOG, CHANGELOG, SECURITY (new §8 entry + posture row + §2 env-var key-detection note), DECISIONS (**D-0022**), and create FUTURE_ROADMAP.md.

### Workflow

Branch `feat/dashboard-settings-ai` → TDD commits → request-code-review pass → finishing-a-development-branch (PR to `main`). **Out of scope (do NOT build):** real provider integrations, external requests, key storage, Learning/Career/Meeting UIs, semantic search.

---

## End-of-slice report (delivered at completion)

Roadmap status · dashboard maturity · version recommendation · next slice · next 3 milestones · product opportunities discovered.
