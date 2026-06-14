"""Capture the full professional screenshot package (v1.0.0).

DEV-TIME tool only (like PyInstaller/Inno Setup): requires `pip install playwright`
and `python -m playwright install chromium`. The DeveloperOS runtime stays
stdlib-only. Nothing is mocked or fabricated: an isolated workspace is seeded
through the normal application flows (real folder scans + real CSRF-guarded API
writes), and every web capture is the live dashboard after real interactions.
The native desktop-window / installer shots are real captures committed under
docs/screenshots/ and are copied into each set (Playwright cannot grab an OS
window or an Inno Setup dialog).

This is the companion to tools/take_screenshots.py (which still produces the
legacy root gallery). This script produces three curated, 16:9 sets:

  docs/screenshots/github/     8 shots  @ 1280x720  (README-friendly, @2x)
  docs/screenshots/portfolio/  6 shots  @ 1440x810  (premium, @2x)
  docs/screenshots/store/      8 shots  @ 1440x810  (marketing, @2x)

Run from the repo root:  python tools/take_screenshot_package.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "screenshots"
GH = OUT / "github"
PF = OUT / "portfolio"
ST = OUT / "store"
# Demo project workspace: a clean sibling path so captured folder paths read
# "C:\Projects\devos-demo-shots\..." (no username, nothing personal).
DEMO = REPO.parent / "devos-demo-shots"

PORT = 8842  # distinct from the legacy tool (8841)
BASE = f"http://127.0.0.1:{PORT}"

GH_VP = {"width": 1280, "height": 720}
HI_VP = {"width": 1440, "height": 810}
DSF = 2

NATIVE_DESKTOP = OUT / "desktop-window.png"   # real shipped-window capture
NATIVE_INSTALLER = OUT / "installer.png"      # real Inno Setup capture

TRANSCRIPT = """Sprint planning — June 12

Attendees: Dana, Omer, Tal.
We agreed the v1.0 release is ready once the screenshot gallery lands.
Dana walked through the desktop window experience and the installer flow.

Decisions:
- Ship v1.0.0 after the final polish pass.
- Keep cloud AI providers out until the no-cost policy changes.

Action items:
- Add the screenshot gallery to the README
- Verify the installer on a clean machine
TODO: write the v1.0 release notes
"""

# --- realistic sample projects (real files scanned by the real ingest engine) ---

SAMPLE_REPOS = {
    "taskflow-api": {
        "name": "TaskFlow API",
        "files": {
            "README.md": (
                "# TaskFlow API\n\n"
                "A small task-tracking service: REST endpoints over SQLite with JWT auth.\n\n"
                "## Endpoints\n"
                "- `POST /tasks` create a task\n"
                "- `GET /tasks` list tasks (filter by `status`, `priority`)\n"
                "- `POST /auth/login` exchange credentials for a token\n\n"
                "Run with `python app.py`; tokens are signed with `TASKFLOW_SECRET`.\n"
            ),
            "app.py": (
                '"""TaskFlow API — minimal Flask-style service."""\n'
                "from models import TaskStore\n"
                "from auth import issue_token, require_token\n\n"
                "store = TaskStore('tasks.db')\n\n\n"
                "def create_task(request):\n"
                '    """Create a task from a JSON body; requires a valid bearer token."""\n'
                "    user = require_token(request.headers.get('Authorization'))\n"
                "    data = request.get_json()\n"
                "    return store.add(title=data['title'],\n"
                "                     priority=data.get('priority', 'medium'),\n"
                "                     owner=user)\n\n\n"
                "def list_tasks(request):\n"
                '    """Return tasks, optionally filtered by status and priority."""\n'
                "    status = request.args.get('status')\n"
                "    priority = request.args.get('priority')\n"
                "    return store.query(status=status, priority=priority)\n"
            ),
            "models.py": (
                '"""SQLite-backed task storage for TaskFlow."""\n'
                "import sqlite3\n\n\n"
                "class TaskStore:\n"
                "    def __init__(self, path):\n"
                "        self.db = sqlite3.connect(path)\n"
                "        self.db.execute(\n"
                "            'CREATE TABLE IF NOT EXISTS tasks ('\n"
                "            'id INTEGER PRIMARY KEY, title TEXT, priority TEXT,'\n"
                "            \" status TEXT DEFAULT 'todo', owner TEXT)\")\n\n"
                "    def add(self, title, priority, owner):\n"
                "        cur = self.db.execute(\n"
                "            'INSERT INTO tasks(title, priority, owner) VALUES (?,?,?)',\n"
                "            (title, priority, owner))\n"
                "        self.db.commit()\n"
                "        return {'id': cur.lastrowid, 'title': title}\n\n"
                "    def query(self, status=None, priority=None):\n"
                "        sql = 'SELECT id, title, priority, status FROM tasks WHERE 1=1'\n"
                "        args = []\n"
                "        if status:\n"
                "            sql += ' AND status = ?'; args.append(status)\n"
                "        if priority:\n"
                "            sql += ' AND priority = ?'; args.append(priority)\n"
                "        return [dict(zip(('id', 'title', 'priority', 'status'), r))\n"
                "                for r in self.db.execute(sql, args)]\n"
            ),
            "auth.py": (
                '"""Stateless JWT-style token helpers for TaskFlow."""\n'
                "import hashlib\nimport hmac\nimport os\n\n"
                "SECRET = os.environ.get('TASKFLOW_SECRET', 'dev-only')\n\n\n"
                "def issue_token(user):\n"
                '    """Sign a short token for an authenticated user."""\n'
                "    sig = hmac.new(SECRET.encode(), user.encode(), hashlib.sha256)\n"
                "    return user + '.' + sig.hexdigest()[:16]\n\n\n"
                "def require_token(header):\n"
                '    """Validate an Authorization header and return the user."""\n'
                "    if not header or '.' not in header:\n"
                "        raise PermissionError('missing or malformed token')\n"
                "    user, _, sig = header.partition('.')\n"
                "    expected = issue_token(user).split('.')[1]\n"
                "    if not hmac.compare_digest(sig, expected):\n"
                "        raise PermissionError('invalid token')\n"
                "    return user\n"
            ),
            "requirements.txt": "flask>=3.0\npyjwt>=2.8\n",
        },
    },
    "pixelforge": {
        "name": "PixelForge",
        "files": {
            "README.md": (
                "# PixelForge\n\n"
                "A tiny offline-first image-filter playground. Ships as an installable PWA — "
                "drop an image, tweak filters, export. No uploads; everything runs in the browser.\n\n"
                "## Stack\n"
                "- Vanilla JS + Canvas 2D\n"
                "- Service worker for offline use\n"
            ),
            "index.html": (
                "<!doctype html>\n<html lang=\"en\">\n<head>\n"
                "  <meta charset=\"utf-8\" />\n"
                "  <title>PixelForge</title>\n"
                "  <link rel=\"stylesheet\" href=\"styles.css\" />\n"
                "  <link rel=\"manifest\" href=\"manifest.webmanifest\" />\n"
                "</head>\n<body>\n"
                "  <main id=\"app\">\n"
                "    <canvas id=\"stage\" width=\"640\" height=\"480\"></canvas>\n"
                "  </main>\n"
                "  <script src=\"app.js\"></script>\n"
                "</body>\n</html>\n"
            ),
            "app.js": (
                "// PixelForge — canvas image filters, all client-side.\n"
                "const stage = document.getElementById('stage');\n"
                "const ctx = stage.getContext('2d');\n\n"
                "export function applyGrayscale(image) {\n"
                "  ctx.drawImage(image, 0, 0);\n"
                "  const px = ctx.getImageData(0, 0, stage.width, stage.height);\n"
                "  for (let i = 0; i < px.data.length; i += 4) {\n"
                "    const v = 0.3 * px.data[i] + 0.59 * px.data[i + 1] + 0.11 * px.data[i + 2];\n"
                "    px.data[i] = px.data[i + 1] = px.data[i + 2] = v;\n"
                "  }\n"
                "  ctx.putImageData(px, 0, 0);\n"
                "}\n\n"
                "export function applyBrightness(amount) {\n"
                "  const px = ctx.getImageData(0, 0, stage.width, stage.height);\n"
                "  for (let i = 0; i < px.data.length; i += 4) {\n"
                "    px.data[i] += amount; px.data[i + 1] += amount; px.data[i + 2] += amount;\n"
                "  }\n"
                "  ctx.putImageData(px, 0, 0);\n"
                "}\n"
            ),
            "styles.css": (
                ":root { --bg: #0f1117; --fg: #e6e6e6; }\n"
                "body { margin: 0; background: var(--bg); color: var(--fg);\n"
                "  font-family: system-ui, sans-serif; }\n"
                "#app { display: grid; place-items: center; min-height: 100vh; }\n"
                "#stage { border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,.4); }\n"
            ),
            "package.json": (
                "{\n"
                '  "name": "pixelforge",\n'
                '  "version": "0.3.0",\n'
                '  "description": "Offline-first image-filter playground (PWA)",\n'
                '  "scripts": { "dev": "python -m http.server 5173" },\n'
                '  "license": "MIT"\n'
                "}\n"
            ),
        },
    },
}


def post(path: str, body: dict, token: str) -> dict:
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Origin": BASE, "X-DevOS-Token": token},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def task_id(resp: dict, fallback: int) -> int:
    if "task" in resp and isinstance(resp["task"], dict):
        return resp["task"]["id"]
    return resp.get("id", fallback)


def write_sample_repos() -> None:
    """Materialise the demo projects as real files on disk."""
    for slug, spec in SAMPLE_REPOS.items():
        root = DEMO / slug
        root.mkdir(parents=True, exist_ok=True)
        for rel, content in spec["files"].items():
            (root / rel).write_text(content, encoding="utf-8")


def seed(token: str) -> None:
    """Representative demo data created through the normal app flows."""
    # Real folder scans (the real ingest + index engine).
    for slug, spec in SAMPLE_REPOS.items():
        post("/api/projects/scan", {"path": str(DEMO / slug), "name": spec["name"]}, token)
    post("/api/projects/scan", {"path": str(REPO), "name": "DeveloperOS"}, token)

    # Tasks across statuses/priorities — an active board.
    post("/api/tasks/create", {"title": "Write the v1.0 release notes", "priority": "high"}, token)
    post("/api/tasks/create", {"title": "Verify the installer on a clean machine", "priority": "medium"}, token)
    t = post("/api/tasks/create", {"title": "Add the screenshot gallery to the README", "priority": "medium"}, token)
    post("/api/tasks/update", {"id": task_id(t, 3), "status": "in_progress"}, token)
    a = post("/api/tasks/create", {"title": "Add OAuth refresh to TaskFlow API", "priority": "high"}, token)
    post("/api/tasks/update", {"id": task_id(a, 4), "status": "in_progress"}, token)
    post("/api/tasks/create", {"title": "Polish PixelForge empty states", "priority": "low"}, token)
    post("/api/tasks/create", {"title": "Triage flaky auth test", "priority": "medium"}, token)

    # Notes / long-term memory.
    post("/api/notes/create", {"title": "Decision: dark-only UI",
                               "body": "OLED dark theme fits a developer tool; recorded in D-0027."}, token)
    post("/api/notes/create", {"title": "TaskFlow API signs tokens with HMAC-SHA256",
                               "body": "Secret comes from TASKFLOW_SECRET; tokens are stateless."}, token)
    post("/api/notes/create", {"title": "PixelForge ships as an installable PWA",
                               "body": "Service worker caches the shell; all filters run client-side."}, token)

    # Job leads — career tab populated.
    post("/api/jobs/create", {"company": "Acme Robotics", "role": "Senior Python Developer",
                              "status": "interview",
                              "notes": "Python, SQLite, FTS5, local-first architecture, "
                                       "accessibility, CI on GitHub Actions."}, token)
    post("/api/jobs/create", {"company": "Northwind", "role": "Backend Engineer",
                              "status": "applied",
                              "notes": "REST APIs, authentication, JWT, test-driven development."}, token)


def main() -> int:
    from playwright.sync_api import sync_playwright

    for d in (GH, PF, ST):
        d.mkdir(parents=True, exist_ok=True)

    if not NATIVE_DESKTOP.is_file() or not NATIVE_INSTALLER.is_file():
        print("ERROR: native captures missing under docs/screenshots/ "
              "(desktop-window.png / installer.png).", file=sys.stderr)
        return 1

    home = tempfile.mkdtemp(prefix="devos_pkg_")
    env = dict(os.environ, DEVOS_HOME=home)
    devos = shutil.which("devos") or "devos"
    if DEMO.exists():
        shutil.rmtree(DEMO, ignore_errors=True)
    write_sample_repos()

    subprocess.run([devos, "init"], env=env, check=True, capture_output=True)
    server = subprocess.Popen([devos, "serve", "--port", str(PORT)], env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(BASE + "/api/overview", timeout=1)
                break
            except Exception:
                time.sleep(0.2)
        with urllib.request.urlopen(BASE + "/api/session", timeout=5) as r:
            token = json.loads(r.read())["token"]
        seed(token)

        with sync_playwright() as p:
            browser = p.chromium.launch()

            def shot(page, target: Path) -> None:
                page.wait_for_timeout(450)  # settle fonts/transitions
                page.screenshot(path=str(target))
                print(f"captured {target.relative_to(OUT)}")

            # --- navigation flows (each leaves the page on the named screen) ---
            def nav_home(page):
                page.click("#tab-home")
                page.wait_for_selector(".welcome")
                page.wait_for_selector(".stat .n")
                page.evaluate("window.scrollTo(0, 0)")

            def nav_deepdive(page):
                page.click("#tab-projects")
                page.wait_for_selector(".projcard")
                # DeveloperOS has the richest content + a clean folder path.
                page.click(".projcard:has(h2:text-is('DeveloperOS')) button:has-text('View')")
                page.wait_for_selector("button:has-text('Study this project')")
                page.click("button:has-text('Study this project')")
                page.wait_for_selector(".answer, .panel h2", timeout=30000)
                page.wait_for_timeout(1800)  # study aggregator sections settle
                page.evaluate("window.scrollTo(0, 0)")

            def nav_search_ask(page):
                page.click("#tab-assist")
                page.fill("#search-q", "ollama provider")
                page.click("form:has(#search-q) button[type=submit]")
                page.wait_for_selector(".snippet", timeout=30000)
                page.fill("#ask-q", "How does the launcher decide if a port is free?")
                page.click("form:has(#ask-q) button[type=submit]")
                page.wait_for_selector(".answer", timeout=30000)
                page.evaluate("window.scrollTo(0, 0)")

            def nav_learning(page):
                page.click("#tab-learning")
                page.fill("#learn-target", "devos/providers/ollama.py")
                page.click("button:has-text('Explain it')")
                page.wait_for_selector(".answer", timeout=30000)
                page.evaluate("window.scrollTo(0, 0)")

            def nav_career(page):
                page.click("#tab-career")
                page.wait_for_selector("text=Acme Robotics", timeout=15000)
                page.evaluate("window.scrollTo(0, 0)")

            def nav_meeting(page):
                page.click("#tab-meeting")
                page.fill("#mtg-text", TRANSCRIPT)
                page.click("button:has-text('Summarize')")
                page.wait_for_selector("text=Action items → tasks", timeout=30000)
                # Lead with the headline feature: scroll the action-items → tasks
                # bridge up so the checklist + "create tasks" control are in frame
                # (a little summary/decisions context stays visible above it).
                page.evaluate(
                    "() => { const h = [...document.querySelectorAll('h2')]"
                    ".find(e => e.textContent.includes('Action items')); "
                    "if (h) { const y = h.getBoundingClientRect().top "
                    "+ window.scrollY - 150; window.scrollTo(0, y); } }")
                page.wait_for_timeout(300)

            def nav_settings(page, scroll="top"):
                page.click("#tab-settings")
                page.wait_for_selector(".statusrow")
                page.wait_for_selector(".provrow")
                if scroll == "providers":
                    # Align the provider catalog near the top so it dominates the
                    # frame (distinct from the System-status / privacy shot).
                    page.evaluate(
                        "() => { const r = document.querySelector('.provrow');"
                        " if (r) { const y = r.getBoundingClientRect().top "
                        "+ window.scrollY - 110; window.scrollTo(0, y); } }")
                    page.wait_for_timeout(300)
                else:
                    page.evaluate("window.scrollTo(0, 0)")

            def scroll_to_stats(page):
                # Bring the live overview cards to the top of the frame.
                page.evaluate(
                    "() => { const s = document.querySelector('.stat');"
                    " if (s) { const y = s.getBoundingClientRect().top "
                    "+ window.scrollY - 36; window.scrollTo(0, y); } }")
                page.wait_for_timeout(300)

            # ============ GitHub set (1280x720 @2x) ============
            ctx = browser.new_context(viewport=GH_VP, device_scale_factor=DSF)
            page = ctx.new_page()
            page.goto(BASE)
            page.wait_for_selector(".welcome")

            nav_home(page);        shot(page, GH / "dashboard-home.png")
            nav_deepdive(page);    shot(page, GH / "project-deep-dive.png")
            nav_search_ask(page);  shot(page, GH / "search-ask.png")
            nav_learning(page);    shot(page, GH / "learning-center.png")
            nav_career(page);      shot(page, GH / "career-center.png")
            nav_meeting(page);     shot(page, GH / "meeting-summary.png")
            nav_settings(page);    shot(page, GH / "settings-ai.png")
            ctx.close()

            # ============ Portfolio + Store sets (1440x810 @2x) ============
            ctx = browser.new_context(viewport=HI_VP, device_scale_factor=DSF)
            page = ctx.new_page()
            page.goto(BASE)
            page.wait_for_selector(".welcome")

            # Portfolio.
            nav_home(page);        shot(page, PF / "hero.png")
            shot(page, ST / "welcome-experience.png")          # same Home/welcome frame
            scroll_to_stats(page); shot(page, PF / "dashboard-overview.png")
            nav_search_ask(page);  shot(page, PF / "ai-features.png")
            shot(page, ST / "search-your-code.png")            # same Search&Ask frame
            nav_learning(page);    shot(page, PF / "learning-features.png")
            shot(page, ST / "learn-any-project.png")           # same Learn frame
            nav_career(page);      shot(page, PF / "career-features.png")
            shot(page, ST / "career-assistant.png")            # same Career frame

            # Store-only screens.
            nav_meeting(page);                   shot(page, ST / "meeting-notes-to-tasks.png")
            nav_settings(page, "top");           shot(page, ST / "privacy-local-first.png")
            nav_settings(page, "providers");     shot(page, ST / "ai-provider-support.png")
            ctx.close()

            browser.close()

        # ============ Native shots (copied real captures) ============
        shutil.copyfile(NATIVE_DESKTOP, GH / "desktop-window.png")
        shutil.copyfile(NATIVE_DESKTOP, PF / "desktop-experience.png")
        shutil.copyfile(NATIVE_DESKTOP, ST / "desktop-app-experience.png")
        print("copied native desktop-window capture into all three sets")

    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except Exception:
            server.kill()
        shutil.rmtree(home, ignore_errors=True)
        shutil.rmtree(DEMO, ignore_errors=True)
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
