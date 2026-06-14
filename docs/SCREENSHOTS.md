# Screenshots

Every image here is a **real capture of the running DeveloperOS v1.0.0 app** — no
mockups, no placeholders, no fabricated UI. The web shots are the live local
dashboard (offline mock provider — exactly what ships) driven through normal flows;
the desktop-window and installer shots are real OS captures of the shipped product.

The package is split into three curated, 16:9 sets for different audiences.

## How they're generated

```
pip install playwright
python -m playwright install chromium
python tools/take_screenshot_package.py
```

The driver (`tools/take_screenshot_package.py`, dev-time only — the runtime stays
stdlib-only) spins up an **isolated** workspace (`DEVOS_HOME` in a temp dir),
generates a few small **real** sample repos (`TaskFlow API`, `PixelForge`) plus
scans this repository, seeds realistic tasks / notes / job-leads through the normal
**CSRF-guarded API**, then captures each screen with Playwright at two viewport
sizes. The native desktop-window / installer shots can't be produced by a browser,
so the committed real captures (`desktop-window.png`, `installer.png`) are copied
into each set. Nothing personal is shown: synthetic demo data, clean
`C:\Projects\...` folder paths, headless browser (no tabs / OS chrome).

## Folder structure

```
docs/screenshots/
├── github/                     8 shots · 2560×1440 (1280×720 @2x) · README gallery
│   ├── dashboard-home.png
│   ├── project-deep-dive.png
│   ├── search-ask.png
│   ├── learning-center.png
│   ├── career-center.png
│   ├── meeting-summary.png
│   ├── settings-ai.png
│   └── desktop-window.png      (copied real native-window capture)
├── portfolio/                  6 shots · 2880×1620 (1440×810 @2x) · premium showcase
│   ├── hero.png
│   ├── dashboard-overview.png
│   ├── ai-features.png
│   ├── learning-features.png
│   ├── career-features.png
│   └── desktop-experience.png  (copied real native-window capture)
├── store/                      8 shots · 2880×1620 (1440×810 @2x) · marketing / landing
│   ├── welcome-experience.png
│   ├── search-your-code.png
│   ├── learn-any-project.png
│   ├── meeting-notes-to-tasks.png
│   ├── career-assistant.png
│   ├── desktop-app-experience.png  (copied real native-window capture)
│   ├── privacy-local-first.png
│   └── ai-provider-support.png
├── desktop-window.png          1313×995  · real shipped app-mode window (Edge --app)
├── installer.png               814×623   · real Inno Setup installer dialog
└── *.png                       legacy root gallery (kept; the original real captures)
```

## GitHub set — `docs/screenshots/github/` (2560×1440)

Embedded in the README; clean, crisp, README-friendly.

| File | Screen | Purpose |
|---|---|---|
| `dashboard-home.png` | Home | Welcome guide + live overview — the first impression. |
| `project-deep-dive.png` | Projects → Study | Per-project Deep Dive: start-here files, key files, study. |
| `search-ask.png` | Search & Ask | Ranked code search + grounded answer cited as `file:line`. |
| `learning-center.png` | Learn | Leveled explanation of a real file, with sources. |
| `career-center.png` | Career | Job-lead tracking + interview prep + CV check. |
| `meeting-summary.png` | Meeting | Transcript → summary → **action items → tasks** bridge. |
| `settings-ai.png` | Settings | System status (local-first, v1.0.0) + AI provider catalog. |
| `desktop-window.png` | Native window | The standalone desktop app window — no browser chrome. |

## Portfolio set — `docs/screenshots/portfolio/` (2880×1620)

Premium framing for portfolio sites, recruiters, and LinkedIn.

| File | Screen | Purpose |
|---|---|---|
| `hero.png` | Home (welcome) | The showcase shot — lead image for a case study. |
| `dashboard-overview.png` | Home (overview) | Live stats, recent activity, multiple projects — an active workspace. |
| `ai-features.png` | Search & Ask | The AI story: grounded, cited answers from your own code. |
| `learning-features.png` | Learn | Learning-from-your-code capability. |
| `career-features.png` | Career | Career tooling depth (job leads, prep, CV). |
| `desktop-experience.png` | Native window | "It's a real desktop app," not just a web page. |

## Store / marketing set — `docs/screenshots/store/` (2880×1620)

Feature-framed for future store listings or a landing page.

| File | Screen | Purpose |
|---|---|---|
| `welcome-experience.png` | Home (welcome) | Onboarding / first-run story. |
| `search-your-code.png` | Search & Ask | "Search your code" feature panel. |
| `learn-any-project.png` | Learn | "Learn any project" feature panel. |
| `meeting-notes-to-tasks.png` | Meeting | "Meeting notes → tasks" feature panel. |
| `career-assistant.png` | Career | "Career assistant" feature panel. |
| `desktop-app-experience.png` | Native window | "Real desktop app" feature panel. |
| `privacy-local-first.png` | Settings (status) | "Privacy & local-first" — data stays on your machine. |
| `ai-provider-support.png` | Settings (providers) | "AI on your terms" — provider catalog, keys never stored. |

## Recommended usage

- **GitHub README** — the `github/` set (already embedded). Lead with
  `desktop-window.png`, then the 2×4 feature grid.
- **Portfolio website** — `portfolio/hero.png` as the case-study lead, then
  `dashboard-overview.png`, `ai-features.png`, `desktop-experience.png`.
- **LinkedIn** — `portfolio/hero.png` or `portfolio/dashboard-overview.png`
  (highest visual impact in-feed); `desktop-experience.png` for the "real app" angle.
- **Resume / portfolio links** — link to this file or the `portfolio/` set.
- **Store listings / landing pages** — the `store/` set, in feature order.

## Regenerating

Re-running `python tools/take_screenshot_package.py` deterministically rebuilds all
three sets. The README gallery is pinned by `tests/test_ui_static.py`
(`test_readme_screenshots_exist`) — every screenshot the README references must
exist on disk, so the gallery can never drift into broken links or fabrications.
