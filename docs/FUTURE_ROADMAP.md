# DeveloperOS — Future Product Roadmap

_Last updated: 2026-06-02 · Product-management view. **Planning only — nothing here is built yet.**_

> This document looks **beyond** the delivered roadmap (`ROADMAP.md`, Phases 0–9 + dashboard slices 1–5).
> It is written from a **Lead Architect + Product Manager** lens: it weighs user value, usability,
> onboarding, learning curve, maintainability, and long-term strategy — not just engineering feasibility.
> It **extends** `ROADMAP.md`; it does not replace or fork it. Every item is prioritized so a future
> session can pick the highest-leverage work without re-deciding the product.

## Prioritization legend
- **[Core]** — Core Product. Defines what DeveloperOS *is*; required for a credible v1.0.
- **[High]** — High Value. Strong user value or differentiation; schedule soon after core.
- **[Nice]** — Nice To Have. Real but incremental; do when cheap or when it unblocks something bigger.
- **[Research]** — Future Research. Promising but unproven/expensive; needs a spike before commitment.

Guiding principle (unchanged from the brief): **local-first, private by default, grounded not guessing,
safe actions only with explicit consent.** Every idea below inherits those constraints.

---

## 1. Product vision

### Where we are today (v0.5.0)
A local-first, offline, **CLI + loopback dashboard** for understanding and working a codebase: scan/index,
keyword search, grounded Q&A, debug assistant, tasks & memory, docgen, learning/career/meeting modules,
a plugin seam, and a maturing dashboard (Home · Tasks · Notes · Search & Ask · Debug · Projects · Study ·
**Settings**). AI is an offline mock by design — no key, nothing leaves the machine.

### Vision for v1.0 — "Your codebase, understood and under control, on your machine"
The polished, trustworthy daily driver for a single developer.
- **One real AI provider, opt-in and safe** [Core] — wire **one** provider (likely local **Ollama** first
  for the privacy story, then **Claude**) behind the existing `providers.ai` seam. Keys from env/keychain;
  a clear in-dashboard consent step before the first outbound call; offline mock stays the default.
- **Dashboard reaches feature-parity with the CLI** [Core] — Learning tab, Career tab, Meeting tab, and
  CRUD polish (deletes, project pickers, edit-in-place) so a non-technical user never needs the terminal.
- **Trustworthy grounding everywhere** [Core] — every AI surface cites `file:line`, declines when
  unsure, and visibly distinguishes "from your code" vs "model commentary."
- **Onboarding that earns trust in 60 seconds** [Core] — first-run flow: pick a folder → scan/index →
  "ask your first question," with privacy/cost stated up front (the Settings work is the foundation).
- **Polish & accessibility** [High] — design-system pass, keyboard nav, ARIA, responsive, empty/error
  states, dark/light themes.

### Vision for v2.0 — "From understanding to safe action, and beyond one machine"
- **Safe Action Agent** [Core for v2] — propose-and-confirm edits/refactors/git ops, workspace-scoped,
  diff-previewed, reversible (branches over destruction). This is the brief's headline capability.
- **Editor/Terminal presence** [High] — VS Code extension + richer TUI so DeveloperOS meets developers
  where they work, reusing the same local API.
- **Semantic search** [High] — embeddings backend behind the D-0006 seam for meaning-based retrieval.
- **Optional, encrypted multi-device sync** [Research] — opt-in, end-to-end encrypted; never a default.
- **Team mode** [Research] — shared project memory/decisions with per-user isolation and RBAC.

---

## 2. Dashboard roadmap

IA target (from D-0021): **Work · Understand · Grow · System.**
- ✅ Work: Home, Tasks, Notes. ✅ Understand: Search & Ask, Debug, Projects, Study. ✅ System: Settings.
- **Learning tab** [Core] — surface `modules/learning` (learn / quiz / exercise / grade) for a project.
- **CRUD polish** [Core] — delete tasks/notes, project pickers on create, inline edit, confirm-destructive.
- **Career tab** [High] — `modules/career` (job leads, CV keyword match, interview prep).
- **Meeting tab** [High] — `modules/meeting.summarize` (paste/upload notes → summary/decisions/actions),
  and a "turn action items into tasks" bridge [High].
- **Plugins/Extensions UI** [Nice] — list loaded plugins, show errors, toggle the local-plugin opt-in.
- **Design-system + a11y pass** [High] — tokens, components, keyboard/ARIA, theming, responsive.
- **Activity timeline & insights** [Nice] — richer "where I left off," streaks, weekly digest.
- **Command palette / global search** [Nice] — fast keyboard navigation across tabs and data.

## 3. AI roadmap
- **Real provider integration (Ollama → Claude → OpenAI)** [Core] — implement behind `register_provider`;
  per-call **consent + cost/latency surfacing**; graceful fallback to mock on error/missing key.
- **Audit log for outbound calls** [Core, ships with first real provider] — local, redacted (provider,
  model, token counts, timestamps — never prompt/secret contents); user-inspectable (SECURITY §6).
- **Prompt-injection hardening for live models** [Core, with real providers] — enforce the grounding
  contract at the provider boundary; no ambient authority; context is data, never executed (SECURITY §5).
- **Streaming responses + cancel** [High] — responsive UX for long answers.
- **Model/endpoint selection + per-task model routing** [High] — cheap model for search, stronger for
  reasoning; the Settings provider-config panel is already prepared for this.
- **Secret-aware indexing** [High] — skip/redact likely-secret files (`.env`, keys) before chunking
  (SECURITY §2 PLANNED).
- **Embeddings / semantic search** [Research] — local-first embedding model behind the D-0006 seam.
- **Multi-agent / tool-use orchestration** [Research] — only after the Safe Action Agent exists.

## 4. Productivity roadmap
- **Action items → tasks** bridge (from Meeting/Debug) [High].
- **Git intelligence** [High] — summarize diffs, draft commit messages/PR descriptions, explain blame
  (read-only first; writes go through the Safe Action Agent).
- **Safe Action Agent** [Core for v2] — the propose/confirm/preview/apply loop (SECURITY §4).
- **Templated workflows / "recipes"** [Nice] — e.g. "onboard me to this repo" runs scan→explain→study.
- **Reminders / scheduled digests** [Nice] — "what changed / what's blocked" summaries.
- **Time & focus tracking** [Research] — lightweight, local, privacy-respecting.

## 5. Learning roadmap
- **Learning tab** (explain/quiz/exercise/grade in the UI) [Core].
- **Persisted progress** [High] — store quiz/exercise scores and a per-project mastery view (new tables;
  same local/git-ignored model).
- **Guided "learn this repo" path** [High] — sequenced Study → quiz → exercise with checkpoints.
- **Spaced repetition** over saved questions [Nice].
- **Personalized difficulty** from past performance [Research].

## 6. Career roadmap
- **Career tab** (job leads, CV keyword match, interview prep) [High].
- **Project → portfolio/resume bullets** [High] — grounded, generated from indexed projects + memory.
- **CV rewrite / cover-letter drafting** [Nice] — grounded, user-edited; **no scraping, no paid APIs**
  (explicitly excluded by current policy).
- **Mock-interview mode** [Nice] — interactive Q&A from `interview_prep`.
- **Job-board integrations** [Research] — only if it can respect the no-scraping/privacy stance.

## 7. Enterprise roadmap (all gated behind multi-user/cloud, far future)
- **Multi-user accounts + per-user data isolation + RBAC** [Research] (SECURITY §3).
- **Encryption at rest** (SQLCipher / field-level for sensitive tables) [Research] (SECURITY §7).
- **Team shared memory/decisions** with ownership checks [Research].
- **SSO / audit/compliance exports** [Research].
- **Self-hosted server deployment** [Research] — TLS, rate limiting, networked-surface hardening.

> Enterprise is **deliberately last.** It introduces the biggest security surface (auth, network, shared
> data) and contradicts the single-power-user simplicity that makes today's product trustworthy. Do not
> start until the single-user product is excellent and a real customer need is proven.

## 8. Stretch goals
- Voice/STT for the Meeting assistant (action-item capture) [Research].
- Browser extension for "explain this snippet/error" [Research].
- Plugin marketplace **after** sandboxing/permissions/signing land [Research] (SECURITY §5 PLANNED).
- Offline local-LLM bundle for a zero-config private AI experience [Research].
- Cross-project knowledge graph ("where else do we do X?") [Research].

## 9. Ideas backlog (unsorted, revisit each planning session)
- Inline "explain this file" from the Projects tree.
- Saved searches / pinned questions.
- Export a project's Study Deep Dive to Markdown/PDF.
- Health checks: stale index detection, "re-scan suggested."
- Keyboard-first power-user mode in the dashboard.
- Theming / branding for portfolio screenshots.
- Telemetry **opt-in only**, fully local, never default (consistent with §0 principles).

---

## How to use this document
1. At each `/plan`, pick the **highest-priority unblocked item** for the relevant area (prefer **[Core]**,
   then **[High]**).
2. Keep slices narrow and shippable; reuse existing modules/seams; never fork a parallel system.
3. When an item is committed, record the decision in `DECISIONS.md` and move execution detail to
   `TODO.md` / `AGENT_STATE.md`. This file stays strategic, not a task tracker.
4. Re-prioritize freely as real usage teaches us what matters — these tags are a starting hypothesis,
   not a contract.
