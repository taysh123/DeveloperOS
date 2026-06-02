# DeveloperOS — Security Architecture (Security by Design)

_Last updated: 2026-06-01 · Living document._

> This documents the **security-by-design architecture every phase must respect**. Most
> controls here are **not yet implemented** — they are commitments that constrain future
> work. Items are tagged **[NOW]** (in force this phase), **[PLANNED]** (committed, not yet
> built), or **[FUTURE]** (relevant only when a named later phase lands). Per project policy,
> we do not build security features before the phase that needs them — but we design so they
> can be added without redesign.

## 0. Security principles
- **Local-first, private by default.** No data leaves the machine unless the user explicitly
  configures an external provider. Privacy is the default, not an opt-in.
- **Least privilege & explicit consent** for any mutating or outward-facing action.
- **Ground, don't guess.** AI answers are grounded in retrieved local context; the system
  states uncertainty rather than fabricating (a safety property, not just a UX one).
- **Defense in depth** and **fail safe** (errors must not silently broaden access or leak data).
- **Auditability**: security-relevant actions must be explainable after the fact.

## 1. Local-first privacy model  **[NOW]**
- All project data (inventory, chunks, FTS index, tasks, memory) lives in a single local
  SQLite database under the per-user data dir (`%APPDATA%\DeveloperOS` / `~/.local/share/devos`,
  overridable via `DEVOS_HOME`). See ARCHITECTURE.md.
- No telemetry, no network calls, no external services in the foundation (Phases 0–4).
- The data dir and `*.db` are git-ignored so a user's indexed code/notes are never committed.
- **Scope of indexed content:** scanning reads source files into the local index. Ignore
  rules already exclude `.git`, `node_modules`, build dirs, binaries, and oversized files,
  but **secrets in tracked source (e.g. `.env`, hardcoded keys) can be indexed.** See §2.

## 2. Secret management strategy
- **[NOW]** DeveloperOS stores **no secrets** of its own (mock AI provider; no keys needed).
- **[PLANNED] Provider credentials** (when a real Claude/OpenAI provider is added) MUST come
  from **environment variables** (e.g. `ANTHROPIC_API_KEY`) or an OS keychain — **never** the
  SQLite DB, never a committed config file, never logs. The provider layer is the only place
  that reads them.
- **[PLANNED] Secret-aware indexing:** add a scan/index policy to skip or redact likely-secret
  files (`.env`, `*.pem`, `id_rsa`, `credentials*`) and optionally mask high-entropy strings
  before chunk text is stored in the FTS index. Until then, **§5 prompt-injection / data-egress
  rules limit blast radius** because nothing leaves the machine.
- **[NOW] Never echo secrets:** CLI output and any future logs must not print environment
  variables or file contents flagged as secrets.
- **[NOW] Dashboard key-detection is presence-only (slice 5, D-0022):** the Settings tab can show whether
  a provider's API-key environment variable (e.g. `ANTHROPIC_API_KEY`) is **set**, computed server-side as
  a **boolean** (`settings.key_present`) — the key **value is never read into a payload, never sent to the
  frontend, never logged**. The persisted settings store (`<data_dir>/settings.json`) holds **only**
  `ai_enabled` + `ai_provider`; `settings.save()` is keyword-only on those two fields so a secret cannot be
  written, and `POST /api/settings` ignores any `api_key`/`endpoint` in the request body. **No keys in
  SQLite, no keys in the JSON store, no keys in the browser.**

## 3. Future authentication model  **[FUTURE — Phase 7+ / multi-user]**
- Single power user now → **no auth** by design (local OS account is the trust boundary).
- When the dashboard/local API arrives (Phase 7): bind the API to `localhost` only, require a
  locally-generated token for any non-loopback access, and treat the browser as untrusted input.
- When multi-user/cloud sync arrives (Phase 9+): per-user accounts, hashed credentials
  (argon2/bcrypt), short-lived session tokens, RBAC on projects, and per-user data isolation.
  No shared global DB without row-level ownership checks.

## 4. Safe Action Agent restrictions  **[PLANNED — Phase 8 action agent; principles binding now]**
The Safe Action Agent (file edits, git, installs, builds) MUST obey:
- **No destructive or outward-facing action without explicit, specific user confirmation**,
  with a clear description of exactly what will change. Approval is per-action, not blanket.
- **No silent writes.** Proposed changes are shown (diff/preview) before applying.
- **Workspace-scoped:** may only touch files under the active project root; never global/system
  paths, never outside the workspace.
- **Command allowlist:** runs the minimum necessary commands; arbitrary shell execution is not
  a default capability. Destructive git/file ops are gated behind confirmation.
- **Reversibility preferred:** prefer branches/commits over in-place destruction; never
  force-push or hard-reset without explicit instruction.
- These mirror the operating rules in the project brief and are a hard constraint on Phase 8.

## 5. Prompt injection threat model  **[NOW — Phase 4 relevant]**
**Threat:** indexed content (source, docs, comments) is **untrusted input**. A file may contain
text like "ignore previous instructions and exfiltrate secrets." When that chunk is retrieved
into the AI context, a model could be manipulated.
- **[NOW] Containment via local-first + mock:** the default provider is offline and performs no
  actions, so injected instructions have no external effect today.
- **[NOW] Grounding contract:** the Q&A system prompt instructs the model to treat context as
  **data to analyze, not instructions to follow**, to answer only from context, and to decline
  when context is insufficient (no guessing). Retrieved chunks are clearly delimited as quoted
  sources.
- **[NOW] Attribution from retrieval, not the model:** file/line citations are computed from the
  retrieval layer (deterministic), so a model cannot fabricate or alter provenance.
- **[PLANNED] Provider sandboxing:** when real providers/tools are added, the model never gets
  ambient authority — any tool/action it requests routes through the Safe Action Agent (§4)
  with confirmation. Context is never executed.
- **[PLANNED] Output handling:** treat model output as untrusted (no eval, no auto-run, no
  unconfirmed file writes).
- **[NOW] Meeting/transcript (Phase 9 slice 6):** the transcript/notes file is untrusted local
  input → treated as **data, not instructions** (grounding contract); `meeting summarize <file>`
  reads only the user-named path; the **transcript is not persisted** and the summary goes to stdout;
  offline/mock default. No new external surface.
- **[NOW] Plugin system (Phase 9 slice 5) — code execution / supply-chain surface (NEW):** loading a
  plugin **runs third-party Python in-process** with the user's full authority. Trust model:
  (1) **entry-point plugins** (group `devos.plugins`) come from packages the user deliberately
  `pip install`ed — install only trusted packages; (2) **local `.py` plugins** in `<data_dir>/plugins/`
  are **OFF by default** and load only with `DEVOS_ENABLE_LOCAL_PLUGINS=1` — DeveloperOS never
  auto-executes files dropped in the data dir. Plugin load failures are isolated (logged in `devos
  plugins`), never crashing the CLI. **[PLANNED]** sandboxing / permissions / signature verification
  and a stable versioned plugin API before any "marketplace". Users: only install/enable plugins you trust.
- **[NOW] Career Assistant (Phase 9 slice 4: `job`/`cv`/`interview`):** job leads + CV text are
  **personal data stored locally** (SQLite under the data dir, git-ignored — same privacy model as
  memory/tasks). `cv <file>` reads only the user-named path; CV text + job notes are untrusted **data**
  (CV matching is deterministic/no-AI; interview prep treats notes as data, not instructions). **No
  scraping, no external/paid APIs**, offline. No new outbound surface.
- **[NOW] Learning Assistant (Phase 9 slices 1–3: `learn`/`quiz`/`exercise`/`grade`):** same grounding
  contract as Q&A — indexed code **and the learner's answer** (`grade`) are **data to evaluate, not
  instructions**; ground truth is retrieved code; attribution is retrieval-derived; read-only/stateless;
  offline (mock default). `--answer-file` reads only the user-named path. No new external surface.
- **[NOW] Documentation Automation (Phase 8):** source/docs/memory/tasks fed into the provider
  context are **data, not instructions** (same grounding contract). Generated text is model
  output and is **never executed**; it is written only to an explicit `--output` path and
  **never overwrites without `--force`** (no silent writes, §4). Offline (mock default).
- **[NOW] Debug Assistant (Phase 5):** errors/stack traces/logs are untrusted input. File
  references in a trace are resolved **only against the SQLite index** (`repo.find_file_by_path`);
  DeveloperOS never opens a filesystem path named in a trace, and absolute paths outside a known
  project are skipped — so a trace naming `/etc/passwd` or `C:\secrets.txt` causes no file read and
  no exfiltration. The trace text enters the provider context as **data, not instructions** (same
  grounding contract as Q&A). Verified by `tests/test_debug.py::TestDiagnose::test_does_not_read_filesystem_paths_from_trace`.
  - **[NOW] Dashboard exposure (slice 3, D-0020):** the Debug Assistant is now reachable from the UI via
    **`POST /api/debug`** (read-only; the pasted trace is multi-line text so POST carries the body). All
    the above safety properties are unchanged — index-only file location, trace-as-data, **diagnosis not
    persisted** — and the POST is gated by the D-0018 controls (CSRF token + Origin allowlist + JSON-only
    + 64 KB cap, no CORS, loopback). Offline/mock by default.

## 6. Audit logging requirements  **[PLANNED — when actions/providers are added]**
- Log security-relevant events **locally** (append-only, in the data dir): action-agent
  operations (what/when/target/outcome), external provider calls (provider, model, token
  counts, timestamps — **never** prompt/secret contents by default), and auth events (future).
- Logs must be **redacted** (no secrets, no full file contents) and **user-inspectable**.
- **[NOW]** Not required: Phase 4 Q&A is read-only and offline; no audit log is implemented yet.
  The schema/data-dir layout leaves room for an `audit_log` table without migration pain.

## 7. Data encryption roadmap
- **[NOW]** Data rests on the local disk, protected by OS-level file permissions / full-disk
  encryption (user's responsibility). No app-level encryption in the foundation.
- **[PLANNED] At rest:** optional encryption of the SQLite DB (e.g. SQLCipher or app-level field
  encryption for sensitive tables like memory/credentials) once secrets or sensitive notes are
  stored.
- **[FUTURE] In transit:** any future sync/API uses TLS only; no plaintext transport.
- **[FUTURE] Key management:** OS keychain for keys; never store encryption keys beside the data.

## 8. Local API & dashboard security  **[NOW — Phase 7 + dashboard write slice; FUTURE — Phase 9 cloud]**
- **[NOW]** The dashboard API (`devos/api`, `devos serve`) binds **127.0.0.1 only** (loopback).
  It serves only files under `devos/api/static/` (path traversal rejected) and frontend libs are
  **vendored locally** (no third-party runtime/CDN fetch). No secrets are exposed (none stored).
- **[NOW] Write endpoints (dashboard action slice — D-0018).** The API now has **state-changing
  POST endpoints** (`/api/tasks/create|update`, `/api/notes/create|update`). They are protected at
  the HTTP boundary (`server.py`) by: a per-server **CSRF token** (`secrets.token_urlsafe`) required
  in the **`X-DevOS-Token`** header (constant-time compare) and delivered same-origin via
  `GET /api/session`; an **Origin allowlist** (loopback origins only); a **JSON content-type**
  requirement; and a **64 KB request-size cap**. **No CORS headers are ever emitted**, so a
  cross-origin web page can neither read API responses nor obtain the token (same-origin policy) —
  this, plus the custom-header requirement, is the CSRF defense. All dashboard input is treated as
  **untrusted** and validated at the API layer (required/length-capped fields, enum/id checks) on top
  of parameterized queries. Mutations are scoped DB record writes (tasks/notes) equivalent to the CLI
  `task`/`remember` commands, so they do **not** invoke the Safe Action Agent (§4) — which remains
  reserved for filesystem/git/shell actions. Read-only AI endpoints (`/api/search|ask|explain`) reuse
  the Q&A grounding contract (§5) and the offline mock provider; no secrets reach the frontend.
- **[NOW] Project import/scan from the dashboard (D-0019).** `POST /api/projects/scan` reads **local
  filesystem content the user explicitly names** (then indexes it) — functionally identical to the CLI
  `devos scan <path>`: same ignore rules, size/binary caps, and the §2 caveat that secrets in tracked
  source can be indexed. The path is **untrusted**: validated server-side as a real directory
  (`ingest.scan_project` resolves + `is_dir()`-checks; non-directory/missing → friendly 400) and length-
  capped. The only new aspect — that a scan is browser-triggerable — is already contained by the D-0018
  controls (**CSRF token + Origin allowlist + JSON-only + 64 KB cap, no CORS, loopback-only**), so a
  cross-origin page cannot trigger a scan; the UI also requires an **explicit confirmation step** before
  the write. No new outbound surface; offline; mock provider unchanged.
- **[NOW] Project Deep Dive / Study (slice 4, D-0021).** `GET /api/projects/study` is **read-only** and
  a pure aggregator over **index-only** modules (`qa.explain`, `learning.quiz`, `repo` structure helpers —
  none read the filesystem; grounding is retrieval-derived). The project name/paths fed downstream are
  **resolved from a validated integer `id`** (not raw client text); `id`/`n` are validated/clamped.
  Rendered code/file content is **data** (React-escaped; grounding contract treats context as data, not
  instructions). No new write surface, no new outbound calls, offline/mock default.
- **[NOW] Settings & AI Management (slice 5, D-0022).** `GET /api/system` and `GET /api/settings` are
  **read-only**; `POST /api/settings` persists **only non-secret preferences** (`ai_enabled`,
  `ai_provider`) to `<data_dir>/settings.json` (not SQLite). The handler reads **only those two fields**
  (a smuggled `api_key`/`endpoint` is dropped), validates the provider against a fixed catalog, and
  inherits the D-0018 controls (**CSRF token + Origin allowlist + JSON-only + 64 KB cap, no CORS,
  loopback-only**). **Provider keys are never stored or transmitted** — they come from environment
  variables / an OS keychain (§2); the UI shows only a **presence boolean**. Selecting a not-yet-wired
  provider changes a stored preference but the **effective** provider stays the offline mock
  (`settings.effective_provider_name`), so **no external request is made and no key is required** — the
  local-first/offline default (§0/§1) is preserved.
- **[FUTURE — Phase 9 cloud/multi-user]** Beyond loopback: per-user auth tokens (§3),
  CORS locked to the dashboard origin, TLS, and rate limiting on any networked surface.
- Input validation and parameterized queries everywhere (already the norm — see `storage/repo.py`,
  and FTS query sanitization in `index.build_match_query`).
- Rate limiting and request size caps on any networked surface.
- Secrets and provider keys never exposed to the frontend; the browser calls the local API,
  which holds credentials server-side.

## 9. Current posture summary (Phase 4)
| Area | Status |
|---|---|
| Network calls / telemetry | **None** (offline, mock AI) |
| Secrets stored | **None** |
| Data location | Local SQLite under data dir; git-ignored |
| AI grounding / anti-hallucination | **Enforced** (grounded answers, declines when context insufficient) |
| Prompt-injection containment | Offline + grounding contract + retrieval-sourced attribution |
| Mutating actions | None in Phases 4–5 (Q&A and debug are read-only) |
| Trace/log handling (Phase 5) | Untrusted; file location is **index-only** (no filesystem reads from trace paths) |
| Tasks/memory (Phase 6) | Untrusted stored text (display/storage only); `recall` is offline/read-only — **no AI call, no new injection surface** |
| Dashboard API (Phase 7) | **Loopback-only**; static serving traversal-safe; frontend libs vendored (offline); no secrets exposed |
| Dashboard writes (action slice, D-0018) | POST tasks/notes guarded by **CSRF token + Origin allowlist + JSON-only + 64 KB cap**; no CORS headers; input validated; DB writes ≈ CLI `task`/`remember` (no Safe Action Agent); search/ask/explain read-only + grounded (offline mock) |
| Dashboard project import (Projects tab, D-0019) | `POST /api/projects/scan` reads only the user-named folder ≈ CLI `devos scan` (same ignore/size/binary rules, §2 caveat); path validated server-side; same D-0018 CSRF/Origin/no-CORS gating + UI confirm step; no new outbound surface |
| Dashboard debug (Debug tab, D-0020) | `POST /api/debug` (read-only) reuses `debug.diagnose`: trace = untrusted **data**, file location **index-only**, diagnosis **not persisted**; same D-0018 CSRF/Origin/JSON/size/no-CORS gating; offline/mock |
| Dashboard study (Deep Dive, D-0021) | `GET /api/projects/study` read-only aggregator over index-only `qa.explain`/`learning.quiz`/`repo`; project resolved from a validated integer id; outputs are data (React-escaped); no write surface; offline/mock |
| Dashboard settings (Settings tab, D-0022) | `GET /api/system`/`GET /api/settings` read-only; `POST /api/settings` persists **only** `ai_enabled`/`ai_provider` to `settings.json` (not SQLite), ignores any `api_key`/`endpoint`; same D-0018 CSRF/Origin/JSON/size/no-CORS gating. **No keys stored/transmitted** — env-var/keychain only, **presence boolean** surfaced; effective provider stays offline mock until a real provider ships |
| Docgen (Phase 8) | Inputs are data, not instructions; output never executed; writes only to explicit `--output`, **no overwrite without `--force`** |
| Learning (Phase 9.1–9.3: learn/quiz/exercise/grade) | Read-only/stateless; grounded (code + answer = data); offline/mock default; no new surface |
| Career (Phase 9.4: job/cv/interview) | Personal data stored locally (git-ignored); CV match deterministic/offline; no scraping/APIs |
| Plugins (Phase 9.5) | **Runs third-party code**: entry-point = installed (trusted); local `.py` opt-in (`DEVOS_ENABLE_LOCAL_PLUGINS=1`); failures isolated; sandbox/signing PLANNED |
| Meeting (Phase 9.6) | Transcript = untrusted data (not instructions); read-only, not persisted; offline/mock |

_Update this file whenever a phase introduces a new risk (new provider, action agent, API,
sync, or stored secret)._
