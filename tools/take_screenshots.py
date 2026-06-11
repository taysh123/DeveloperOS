"""Capture real README screenshots of the running dashboard (final polish, D-0034).

DEV-TIME tool only (like PyInstaller/Inno Setup): requires `pip install playwright`
and `python -m playwright install chromium`. The DeveloperOS runtime stays
stdlib-only. Nothing is mocked or fabricated: a temp workspace is seeded through
the normal application flows (real scan of this repository, real guarded API
writes), and every capture is the live dashboard after real interactions.

Run from the repo root:  python tools/take_screenshots.py
Output: docs/screenshots/*.png (1280x800 @2x)
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
PORT = 8841
BASE = f"http://127.0.0.1:{PORT}"

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


def post(path: str, body: dict, token: str) -> dict:
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Origin": BASE, "X-DevOS-Token": token},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def seed(token: str) -> None:
    """Representative demo data created through the normal app flows."""
    post("/api/projects/scan", {"path": str(REPO), "name": "DeveloperOS"}, token)
    post("/api/tasks/create", {"title": "Write the v1.0 release notes",
                               "priority": "high"}, token)
    post("/api/tasks/create", {"title": "Verify the installer on a clean machine",
                               "priority": "medium"}, token)
    t = post("/api/tasks/create", {"title": "Add the screenshot gallery to the README",
                                   "priority": "medium"}, token)
    post("/api/tasks/update", {"id": t["task"]["id"] if "task" in t else t.get("id", 3),
                               "status": "in_progress"}, token)
    post("/api/notes/create", {"title": "Decision: dark-only UI",
                               "body": "OLED dark theme fits a developer tool; recorded in D-0027."},
         token)
    post("/api/jobs/create", {"company": "Acme Robotics", "role": "Senior Python Developer",
                              "status": "interview",
                              "notes": "Python, SQLite, FTS5, local-first architecture, "
                                       "accessibility, CI on GitHub Actions."}, token)


def main() -> None:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    home = tempfile.mkdtemp(prefix="devos_shots_")
    env = dict(os.environ, DEVOS_HOME=home)
    devos = shutil.which("devos") or "devos"
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
            page = browser.new_page(viewport={"width": 1280, "height": 800},
                                    device_scale_factor=2)
            page.goto(BASE)

            def shot(name: str) -> None:
                page.wait_for_timeout(400)  # settle fonts/transitions
                page.screenshot(path=str(OUT / name))
                print(f"captured {name}")

            # Home — welcome guide + live overview.
            page.wait_for_selector(".welcome")
            page.wait_for_selector(".stat .n")
            shot("dashboard-home.png")

            # Projects -> detail -> Study (Deep Dive).
            page.click("#tab-projects")
            page.wait_for_selector(".projcard")
            page.click(".projcard button:has-text('View')")
            page.wait_for_selector("button:has-text('Study this project')")
            page.click("button:has-text('Study this project')")
            page.wait_for_selector(".answer, .panel h2", timeout=30000)
            page.wait_for_timeout(1500)  # study aggregator sections
            shot("projects-deep-dive.png")

            # Search & Ask — real query + grounded answer.
            page.click("#tab-assist")
            page.fill("#search-q", "ollama provider")
            page.click("form:has(#search-q) button[type=submit]")
            page.wait_for_selector(".snippet", timeout=30000)
            page.fill("#ask-q", "How does the launcher decide if a port is free?")
            page.click("form:has(#ask-q) button[type=submit]")
            page.wait_for_selector(".answer", timeout=30000)
            shot("search-ask.png")

            # Learning Center — explanation with sources.
            page.click("#tab-learning")
            page.fill("#learn-target", "devos/providers/ollama.py")
            page.click("button:has-text('Explain it')")
            page.wait_for_selector(".answer", timeout=30000)
            shot("learning-center.png")

            # Career Center — seeded job lead + prep/CV sections.
            page.click("#tab-career")
            page.wait_for_selector("text=Acme Robotics", timeout=15000)
            shot("career-center.png")

            # Meeting — transcript -> summary + action-items bridge.
            page.click("#tab-meeting")
            page.fill("#mtg-text", TRANSCRIPT)
            page.click("button:has-text('Summarize')")
            page.wait_for_selector("text=Action items", timeout=30000)
            shot("meeting-summary.png")

            # Settings & AI management.
            page.click("#tab-settings")
            page.wait_for_selector(".statusrow")
            page.wait_for_selector(".provrow")
            shot("settings-ai.png")

            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except Exception:
            server.kill()
        shutil.rmtree(home, ignore_errors=True)
    print("done.")


if __name__ == "__main__":
    sys.exit(main())
