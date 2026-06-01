"""Phase 7 — Dashboard local API tests (TDD, stdlib unittest)."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from devos.api import app as api_app
from devos.core.workspace import Workspace
from devos.modules import index as index_mod
from devos.modules import ingest
from devos.storage import repo


def _write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


class ApiTestCase(unittest.TestCase):
    """Isolated home with an indexed project + a couple of tasks and a memory."""

    def setUp(self) -> None:
        self._prev = os.environ.get("DEVOS_HOME")
        self._home = tempfile.TemporaryDirectory()
        os.environ["DEVOS_HOME"] = self._home.name
        self.ws = Workspace.load()
        self.ws.initialize().close()
        self._proj = tempfile.TemporaryDirectory()
        self.root = Path(self._proj.name)
        _write(self.root, "src/app.py", "def main():\n    return 'hello'\n")
        conn = self.ws.connect()
        try:
            self.pid = ingest.scan_project(conn, self.root, name="demo").project_id
            index_mod.index_project(conn, self.pid)
            repo.create_task(conn, self.pid, "Build dashboard", kind="feature",
                             status="in_progress", priority="high")
            repo.create_task(conn, self.pid, "Blocked thing", kind="bug",
                             status="blocked", priority="medium")
            repo.create_task(conn, self.pid, "Todo thing", kind="task",
                             status="todo", priority="low")
            repo.create_memory(conn, self.pid, kind="decision",
                               title="Use stdlib http.server", body="loopback only")
        finally:
            conn.close()

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("DEVOS_HOME", None)
        else:
            os.environ["DEVOS_HOME"] = self._prev
        self._home.cleanup()
        self._proj.cleanup()


class TestOverviewBuilder(ApiTestCase):
    def test_overview_has_counts_projects_blocked_and_left_off(self) -> None:
        conn = self.ws.connect()
        try:
            ov = api_app.overview(conn)
        finally:
            conn.close()
        self.assertEqual(ov["task_counts"]["in_progress"], 1)
        self.assertEqual(ov["task_counts"]["blocked"], 1)
        self.assertEqual(ov["task_counts"]["todo"], 1)
        self.assertEqual(ov["task_counts"]["done"], 0)
        self.assertTrue(any(p["name"] == "demo" for p in ov["projects"]))
        self.assertTrue(any(t["title"] == "Blocked thing" for t in ov["blocked"]))
        # "where I left off" prefers the in_progress task
        self.assertEqual(ov["where_i_left_off"]["task"]["title"], "Build dashboard")
        self.assertTrue(ov["recent_activity"])

    def test_tasks_payload_filters(self) -> None:
        conn = self.ws.connect()
        try:
            payload = api_app.tasks_payload(conn, status="blocked")
        finally:
            conn.close()
        self.assertEqual([t["title"] for t in payload["tasks"]], ["Blocked thing"])

    def test_recall_payload(self) -> None:
        conn = self.ws.connect()
        try:
            payload = api_app.recall_payload(conn, "dashboard")
        finally:
            conn.close()
        self.assertIn("tasks", payload)
        self.assertIn("memory", payload)
        self.assertIn("code", payload)
        self.assertTrue(any("dashboard" in t["title"].lower() for t in payload["tasks"]))


class TestRouting(ApiTestCase):
    def test_api_overview_json(self) -> None:
        resp = api_app.route(self.ws, "/api/overview", {})
        self.assertEqual(resp.status, 200)
        self.assertIn("json", resp.content_type)
        body = json.loads(resp.body)
        self.assertIn("task_counts", body)

    def test_api_tasks_filter(self) -> None:
        resp = api_app.route(self.ws, "/api/tasks", {"status": "blocked"})
        self.assertEqual(resp.status, 200)
        titles = [t["title"] for t in json.loads(resp.body)["tasks"]]
        self.assertEqual(titles, ["Blocked thing"])

    def test_unknown_api_route_404(self) -> None:
        resp = api_app.route(self.ws, "/api/nope", {})
        self.assertEqual(resp.status, 404)

    def test_index_served_at_root(self) -> None:
        resp = api_app.route(self.ws, "/", {})
        self.assertEqual(resp.status, 200)
        self.assertIn("html", resp.content_type)
        self.assertIn(b'id="root"', resp.body)

    def test_static_path_traversal_blocked(self) -> None:
        resp = api_app.route(self.ws, "/static/../../devos/config.py", {})
        self.assertEqual(resp.status, 404)

    def test_static_assets_served(self) -> None:
        for path, ct in [("/static/app.js", "javascript"),
                         ("/static/styles.css", "css"),
                         ("/static/vendor/react.production.min.js", "javascript")]:
            resp = api_app.route(self.ws, path, {})
            self.assertEqual(resp.status, 200, path)
            self.assertIn(ct, resp.content_type, path)
            self.assertTrue(resp.body)


class TestLiveServer(ApiTestCase):
    def test_live_overview_and_index(self) -> None:
        from devos.api import server as api_server
        srv = api_server.create_server("127.0.0.1", 0)
        self.assertEqual(srv.server_address[0], "127.0.0.1")  # loopback only
        port = srv.server_address[1]
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/overview", timeout=5) as r:
                self.assertEqual(r.status, 200)
                self.assertIn("task_counts", json.loads(r.read()))
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as r:
                self.assertEqual(r.status, 200)
        finally:
            srv.shutdown()
            srv.server_close()
            th.join(timeout=5)
