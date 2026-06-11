"""Phase 7 — Dashboard local API tests (TDD, stdlib unittest)."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import urllib.error
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


class TestWriteEndpoints(ApiTestCase):
    def _post(self, path, body):
        return api_app.route(self.ws, path, {}, method="POST", body=body)

    def test_create_task(self) -> None:
        resp = self._post("/api/tasks/create",
                          {"title": "From UI", "priority": "high", "project": "demo"})
        self.assertEqual(resp.status, 201)
        tid = json.loads(resp.body)["id"]
        conn = self.ws.connect()
        try:
            self.assertEqual(repo.get_task(conn, tid)["title"], "From UI")
        finally:
            conn.close()

    def test_create_task_missing_title_400(self) -> None:
        self.assertEqual(self._post("/api/tasks/create", {"title": "  "}).status, 400)

    def test_create_task_invalid_status_400(self) -> None:
        resp = self._post("/api/tasks/create", {"title": "x", "status": "nope"})
        self.assertEqual(resp.status, 400)

    def test_create_task_unknown_project_400(self) -> None:
        resp = self._post("/api/tasks/create", {"title": "x", "project": "ghost"})
        self.assertEqual(resp.status, 400)

    def test_update_task_status(self) -> None:
        conn = self.ws.connect()
        try:
            tid = repo.create_task(conn, None, "T", kind="task", status="todo", priority="low")
        finally:
            conn.close()
        resp = self._post("/api/tasks/update", {"id": tid, "status": "done"})
        self.assertEqual(resp.status, 200)
        self.assertEqual(json.loads(resp.body)["updated"], 1)
        conn = self.ws.connect()
        try:
            self.assertEqual(repo.get_task(conn, tid)["status"], "done")
        finally:
            conn.close()

    def test_update_task_unknown_id_404(self) -> None:
        self.assertEqual(self._post("/api/tasks/update", {"id": 99999, "status": "done"}).status, 404)

    def test_update_task_bad_id_400(self) -> None:
        self.assertEqual(self._post("/api/tasks/update", {"status": "done"}).status, 400)

    def test_create_and_update_note(self) -> None:
        resp = self._post("/api/notes/create", {"title": "Idea", "body": "remember this"})
        self.assertEqual(resp.status, 201)
        mid = json.loads(resp.body)["id"]
        resp = self._post("/api/notes/update", {"id": mid, "body": "updated body"})
        self.assertEqual(resp.status, 200)
        conn = self.ws.connect()
        try:
            row = repo.get_memory(conn, mid)
            self.assertEqual(row["body"], "updated body")
            self.assertEqual(row["title"], "Idea")
        finally:
            conn.close()

    def test_create_note_missing_body_400(self) -> None:
        self.assertEqual(self._post("/api/notes/create", {"title": "x"}).status, 400)

    def test_unknown_post_route_404(self) -> None:
        self.assertEqual(self._post("/api/nope", {}).status, 404)

    def test_get_does_not_hit_post_actions(self) -> None:
        # a write path under GET is just an unknown read route
        self.assertEqual(api_app.route(self.ws, "/api/tasks/create", {}).status, 404)


class TestReadAssistEndpoints(ApiTestCase):
    def test_search_returns_results(self) -> None:
        resp = api_app.route(self.ws, "/api/search", {"q": "main"})
        self.assertEqual(resp.status, 200)
        body = json.loads(resp.body)
        self.assertIn("results", body)
        self.assertTrue(any("app.py" in r["rel_path"] for r in body["results"]))

    def test_ask_grounded_answer_with_sources(self) -> None:
        resp = api_app.route(self.ws, "/api/ask", {"q": "what does main do"})
        self.assertEqual(resp.status, 200)
        body = json.loads(resp.body)
        self.assertTrue(body["grounded"])
        self.assertTrue(body["sources"])

    def test_ask_empty_question_400(self) -> None:
        self.assertEqual(api_app.route(self.ws, "/api/ask", {"q": "  "}).status, 400)

    def test_ask_declines_when_nothing_matches(self) -> None:
        resp = api_app.route(self.ws, "/api/ask", {"q": "zzzqqqnomatch"})
        self.assertEqual(resp.status, 200)
        self.assertFalse(json.loads(resp.body)["grounded"])

    def test_explain_file(self) -> None:
        resp = api_app.route(self.ws, "/api/explain",
                             {"path": str(self.root / "src" / "app.py")})
        self.assertEqual(resp.status, 200)
        self.assertTrue(json.loads(resp.body)["grounded"])


class TestProjectsEndpoints(ApiTestCase):
    def _post(self, path, body):
        return api_app.route(self.ws, path, {}, method="POST", body=body)

    def test_detail_returns_overview(self) -> None:
        resp = api_app.route(self.ws, "/api/projects/detail", {"id": str(self.pid)})
        self.assertEqual(resp.status, 200)
        body = json.loads(resp.body)
        self.assertEqual(body["project"]["name"], "demo")
        self.assertGreaterEqual(body["project"]["file_count"], 1)
        self.assertIn("by_category", body)
        self.assertGreaterEqual(body["index"]["chunks"], 1)

    def test_detail_unknown_id_404(self) -> None:
        self.assertEqual(api_app.route(self.ws, "/api/projects/detail", {"id": "99999"}).status, 404)

    def test_detail_missing_id_400(self) -> None:
        self.assertEqual(api_app.route(self.ws, "/api/projects/detail", {}).status, 400)
        self.assertEqual(api_app.route(self.ws, "/api/projects/detail", {"id": "x"}).status, 400)

    def test_scan_creates_and_indexes(self) -> None:
        newdir = tempfile.TemporaryDirectory()
        self.addCleanup(newdir.cleanup)
        _write(Path(newdir.name), "lib/util.py", "def add(a, b):\n    return a + b\n")
        resp = self._post("/api/projects/scan", {"path": newdir.name, "name": "fresh"})
        self.assertEqual(resp.status, 201)
        body = json.loads(resp.body)
        self.assertEqual(body["project_name"], "fresh")
        self.assertGreaterEqual(body["total"], 1)
        self.assertGreaterEqual(body["indexed_chunks"], 1)
        conn = self.ws.connect()
        try:
            self.assertIsNotNone(repo.project_id_by_name(conn, "fresh"))
        finally:
            conn.close()

    def test_scan_is_idempotent(self) -> None:
        newdir = tempfile.TemporaryDirectory()
        self.addCleanup(newdir.cleanup)
        _write(Path(newdir.name), "a.py", "x = 1\n")
        first = json.loads(self._post("/api/projects/scan", {"path": newdir.name}).body)
        second = json.loads(self._post("/api/projects/scan", {"path": newdir.name}).body)
        self.assertEqual(first["project_id"], second["project_id"])
        conn = self.ws.connect()
        try:
            names = [p["root_path"] for p in repo.list_projects(conn)]
            self.assertEqual(names.count(second["root"]), 1)
        finally:
            conn.close()

    def test_scan_bad_path_400(self) -> None:
        resp = self._post("/api/projects/scan", {"path": "/no/such/folder/xyz123"})
        self.assertEqual(resp.status, 400)

    def test_scan_missing_path_400(self) -> None:
        self.assertEqual(self._post("/api/projects/scan", {}).status, 400)
        self.assertEqual(self._post("/api/projects/scan", {"path": "   "}).status, 400)
        self.assertEqual(self._post("/api/projects/scan", {"path": 123}).status, 400)


class TestDebugEndpoint(ApiTestCase):
    def _post(self, body):
        return api_app.route(self.ws, "/api/debug", {}, method="POST", body=body)

    def test_grounded_diagnosis_from_traceback(self) -> None:
        tb = ('Traceback (most recent call last):\n'
              '  File "src/app.py", line 2, in main\n'
              "    return 'hello'\n"
              'ValueError: boom\n')
        resp = self._post({"trace": tb})
        self.assertEqual(resp.status, 200)
        body = json.loads(resp.body)
        self.assertEqual(body["error_type"], "ValueError")
        self.assertTrue(body["grounded"])
        self.assertTrue(body["frames"])
        self.assertTrue(body["located"])
        self.assertTrue(body["sources"])
        self.assertTrue(body["analysis"])

    def test_declines_when_nothing_indexed_matches(self) -> None:
        tb = ('Traceback (most recent call last):\n'
              '  File "nowhere/ghost.py", line 9, in zzz\n'
              'SomeWeirdError: zzqqxnomatch\n')
        resp = self._post({"trace": tb})
        self.assertEqual(resp.status, 200)
        body = json.loads(resp.body)
        self.assertFalse(body["grounded"])
        self.assertEqual(body["confidence"], "low")
        self.assertTrue(body["analysis"])

    def test_missing_trace_400(self) -> None:
        self.assertEqual(self._post({}).status, 400)

    def test_empty_trace_400(self) -> None:
        self.assertEqual(self._post({"trace": "   "}).status, 400)

    def test_non_string_trace_400(self) -> None:
        self.assertEqual(self._post({"trace": 123}).status, 400)


class TestStudyEndpoint(ApiTestCase):
    def test_study_bundle_for_indexed_project(self) -> None:
        resp = api_app.route(self.ws, "/api/projects/study", {"id": str(self.pid)})
        self.assertEqual(resp.status, 200)
        b = json.loads(resp.body)
        self.assertEqual(b["project"]["name"], "demo")
        self.assertTrue(b["key_files"])
        self.assertTrue(any("app.py" in f["rel_path"] for f in b["key_files"]))
        self.assertIn("categories", b)
        self.assertTrue(b["overview"]["grounded"])
        self.assertTrue(b["overview"]["sources"])
        self.assertTrue(b["questions"]["grounded"])
        self.assertTrue(b["interview_prep"])
        self.assertTrue(any("demo" in line for line in b["interview_prep"]))

    def test_study_clamps_n(self) -> None:
        resp = api_app.route(self.ws, "/api/projects/study", {"id": str(self.pid), "n": "999"})
        self.assertEqual(resp.status, 200)
        self.assertEqual(json.loads(resp.body)["questions"]["n"], 20)

    def test_study_missing_id_400(self) -> None:
        self.assertEqual(api_app.route(self.ws, "/api/projects/study", {}).status, 400)
        self.assertEqual(api_app.route(self.ws, "/api/projects/study", {"id": "x"}).status, 400)

    def test_study_unknown_id_404(self) -> None:
        self.assertEqual(api_app.route(self.ws, "/api/projects/study", {"id": "99999"}).status, 404)

    def test_study_degrades_for_unindexed_project(self) -> None:
        conn = self.ws.connect()
        try:
            bare = repo.upsert_project(conn, "/tmp/bare-proj-xyz", "bareproj")
            conn.commit()
        finally:
            conn.close()
        resp = api_app.route(self.ws, "/api/projects/study", {"id": str(bare)})
        self.assertEqual(resp.status, 200)
        b = json.loads(resp.body)
        self.assertEqual(b["key_files"], [])
        self.assertFalse(b["overview"]["grounded"])
        self.assertTrue(b["interview_prep"])  # still offers generic guidance


class TestSystemAndSettings(ApiTestCase):
    def _post(self, path, body):
        return api_app.route(self.ws, path, {}, method="POST", body=body)

    def test_system_payload_shape(self) -> None:
        resp = api_app.route(self.ws, "/api/system", {})
        self.assertEqual(resp.status, 200)
        b = json.loads(resp.body)
        self.assertTrue(b["local_first"])
        self.assertTrue(b["offline"])
        self.assertIn("version", b)
        self.assertIn("roadmap_phase", b)
        self.assertIn("dashboard_maturity", b)
        self.assertTrue(b["ai_enabled"])
        self.assertEqual(b["provider_effective"], "mock")
        self.assertGreaterEqual(b["indexed_project_count"], 1)
        prov = {p["id"]: p for p in b["providers"]}
        self.assertTrue(prov["mock"]["available"])     # registered today
        self.assertFalse(prov["claude"]["available"])  # not yet implemented

    def test_settings_get_lists_providers_and_key_booleans(self) -> None:
        resp = api_app.route(self.ws, "/api/settings", {})
        self.assertEqual(resp.status, 200)
        b = json.loads(resp.body)
        self.assertEqual(b["ai_provider"], "mock")
        self.assertTrue(b["ai_enabled"])
        for p in b["providers"]:
            self.assertIsInstance(p["key_present"], bool)  # boolean only, never a value
            self.assertNotIn("api_key", p)

    def test_settings_post_updates_and_persists(self) -> None:
        resp = self._post("/api/settings", {"ai_provider": "ollama", "ai_enabled": False})
        self.assertEqual(resp.status, 200)
        b = json.loads(resp.body)
        self.assertEqual(b["ai_provider"], "ollama")
        self.assertFalse(b["ai_enabled"])
        b2 = json.loads(api_app.route(self.ws, "/api/settings", {}).body)
        self.assertEqual(b2["ai_provider"], "ollama")  # persisted across a fresh read

    def test_settings_post_invalid_provider_400(self) -> None:
        self.assertEqual(self._post("/api/settings", {"ai_provider": "ghost"}).status, 400)

    def test_settings_post_ignores_api_key(self) -> None:
        from devos import settings as settings_mod
        self._post("/api/settings", {"ai_provider": "claude", "api_key": "sk-superSecret"})
        raw = (Path(self.ws.config.data_dir) / settings_mod.SETTINGS_FILENAME).read_text(
            encoding="utf-8")
        self.assertNotIn("sk-superSecret", raw)
        self.assertNotIn("api_key", raw)


class TestLearningEndpoints(ApiTestCase):
    def _post(self, path, body):
        return api_app.route(self.ws, path, {}, method="POST", body=body)

    def test_learn_file_mode_grounded(self) -> None:
        resp = api_app.route(self.ws, "/api/learn",
                             {"target": str(self.root / "src" / "app.py")})
        self.assertEqual(resp.status, 200)
        b = json.loads(resp.body)
        self.assertEqual(b["level"], "intermediate")
        self.assertTrue(b["grounded"])
        self.assertTrue(b["sources"])
        self.assertTrue(b["text"])

    def test_learn_respects_level(self) -> None:
        resp = api_app.route(self.ws, "/api/learn", {"target": "main", "level": "eli5"})
        self.assertEqual(resp.status, 200)
        self.assertEqual(json.loads(resp.body)["level"], "eli5")

    def test_learn_invalid_level_400(self) -> None:
        self.assertEqual(
            api_app.route(self.ws, "/api/learn", {"target": "main", "level": "nope"}).status, 400)

    def test_learn_missing_target_400(self) -> None:
        self.assertEqual(api_app.route(self.ws, "/api/learn", {}).status, 400)
        self.assertEqual(api_app.route(self.ws, "/api/learn", {"target": "  "}).status, 400)

    def test_learn_topic_declines_when_no_match(self) -> None:
        resp = api_app.route(self.ws, "/api/learn", {"target": "zzzqqqnomatch"})
        self.assertEqual(resp.status, 200)
        self.assertFalse(json.loads(resp.body)["grounded"])

    def test_quiz_grounded_and_clamps_n(self) -> None:
        resp = api_app.route(self.ws, "/api/quiz", {"target": "main", "n": "999"})
        self.assertEqual(resp.status, 200)
        b = json.loads(resp.body)
        self.assertEqual(b["n"], 20)
        self.assertTrue(b["grounded"])
        self.assertTrue(b["sources"])

    def test_quiz_missing_target_400(self) -> None:
        self.assertEqual(api_app.route(self.ws, "/api/quiz", {}).status, 400)

    def test_exercise_grounded_default_n(self) -> None:
        resp = api_app.route(self.ws, "/api/exercise", {"target": "main"})
        self.assertEqual(resp.status, 200)
        b = json.loads(resp.body)
        self.assertEqual(b["n"], 3)
        self.assertTrue(b["grounded"])

    def test_grade_grounded_with_sources(self) -> None:
        resp = self._post("/api/grade", {"target": "main", "answer": "main returns the string hello"})
        self.assertEqual(resp.status, 200)
        b = json.loads(resp.body)
        self.assertTrue(b["grounded"])
        self.assertTrue(b["sources"])
        self.assertTrue(b["text"])

    def test_grade_missing_answer_400(self) -> None:
        self.assertEqual(self._post("/api/grade", {"target": "main"}).status, 400)
        self.assertEqual(self._post("/api/grade", {"target": "main", "answer": "  "}).status, 400)

    def test_grade_missing_target_400(self) -> None:
        self.assertEqual(self._post("/api/grade", {"answer": "x"}).status, 400)

    def test_grade_non_string_answer_400(self) -> None:
        self.assertEqual(self._post("/api/grade", {"target": "main", "answer": 123}).status, 400)


class TestDeleteEndpoints(ApiTestCase):
    def _post(self, path, body):
        return api_app.route(self.ws, path, {}, method="POST", body=body)

    def test_delete_task(self) -> None:
        conn = self.ws.connect()
        try:
            tid = repo.create_task(conn, None, "to delete", kind="task",
                                   status="todo", priority="low")
        finally:
            conn.close()
        resp = self._post("/api/tasks/delete", {"id": tid})
        self.assertEqual(resp.status, 200)
        self.assertEqual(json.loads(resp.body)["deleted"], 1)
        conn = self.ws.connect()
        try:
            self.assertIsNone(repo.get_task(conn, tid))
        finally:
            conn.close()

    def test_delete_task_unknown_id_404(self) -> None:
        self.assertEqual(self._post("/api/tasks/delete", {"id": 99999}).status, 404)

    def test_delete_task_bad_id_400(self) -> None:
        self.assertEqual(self._post("/api/tasks/delete", {}).status, 400)
        self.assertEqual(self._post("/api/tasks/delete", {"id": "x"}).status, 400)
        self.assertEqual(self._post("/api/tasks/delete", {"id": 0}).status, 400)

    def test_delete_note(self) -> None:
        conn = self.ws.connect()
        try:
            mid = repo.create_memory(conn, None, kind="note", title="bye", body="remove me")
        finally:
            conn.close()
        resp = self._post("/api/notes/delete", {"id": mid})
        self.assertEqual(resp.status, 200)
        self.assertEqual(json.loads(resp.body)["deleted"], 1)
        conn = self.ws.connect()
        try:
            self.assertIsNone(repo.get_memory(conn, mid))
        finally:
            conn.close()

    def test_delete_note_unknown_id_404(self) -> None:
        self.assertEqual(self._post("/api/notes/delete", {"id": 99999}).status, 404)

    def test_repo_delete_project_cascades(self) -> None:
        conn = self.ws.connect()
        try:
            chunks_before, _ = repo.chunk_stats(conn, self.pid)
            self.assertGreater(chunks_before, 0)
            n = repo.delete_project(conn, self.pid)
            self.assertEqual(n, 1)
            self.assertIsNone(repo.get_project(conn, self.pid))
            self.assertEqual(repo.list_tasks(conn, project_id=self.pid), [])
            self.assertEqual(repo.list_memory(conn, project_id=self.pid), [])
            self.assertEqual(repo.list_files(conn, self.pid), [])
            chunks_after, _ = repo.chunk_stats(conn, self.pid)
            self.assertEqual(chunks_after, 0)
            hits = index_mod.search(conn, "main", op="OR")
            self.assertFalse(any(h.project == "demo" for h in hits))  # FTS reconciled
        finally:
            conn.close()

    def test_delete_project_endpoint_cascades(self) -> None:
        resp = self._post("/api/projects/delete", {"id": self.pid})
        self.assertEqual(resp.status, 200)
        self.assertEqual(json.loads(resp.body)["deleted"], 1)
        conn = self.ws.connect()
        try:
            self.assertIsNone(repo.get_project(conn, self.pid))
            self.assertEqual(repo.list_tasks(conn, project_id=self.pid), [])
        finally:
            conn.close()
        # a search that used to find the project's code now returns nothing for it
        body = json.loads(api_app.route(self.ws, "/api/search", {"q": "main"}).body)
        self.assertFalse(any(r["project"] == "demo" for r in body["results"]))

    def test_delete_project_unknown_id_404(self) -> None:
        self.assertEqual(self._post("/api/projects/delete", {"id": 99999}).status, 404)

    def test_delete_project_bad_id_400(self) -> None:
        self.assertEqual(self._post("/api/projects/delete", {}).status, 400)
        self.assertEqual(self._post("/api/projects/delete", {"id": "x"}).status, 400)

    def test_get_does_not_hit_delete_actions(self) -> None:
        self.assertEqual(api_app.route(self.ws, "/api/tasks/delete", {}).status, 404)
        self.assertEqual(api_app.route(self.ws, "/api/projects/delete", {}).status, 404)


class TestCareerEndpoints(ApiTestCase):
    def _post(self, path, body):
        return api_app.route(self.ws, path, {}, method="POST", body=body)

    def _make_job(self, **kw):
        body = {"company": "Acme", "role": "Engineer", "status": "saved"}
        body.update(kw)
        return json.loads(self._post("/api/jobs/create", body).body)["id"]

    def test_create_job_and_list(self) -> None:
        jid = self._make_job(notes="python, sql")
        resp = api_app.route(self.ws, "/api/jobs", {})
        self.assertEqual(resp.status, 200)
        jobs = json.loads(resp.body)["jobs"]
        self.assertTrue(any(j["id"] == jid and j["company"] == "Acme" for j in jobs))

    def test_create_job_missing_company_400(self) -> None:
        self.assertEqual(self._post("/api/jobs/create", {"company": "  "}).status, 400)
        self.assertEqual(self._post("/api/jobs/create", {}).status, 400)

    def test_create_job_invalid_status_400(self) -> None:
        self.assertEqual(self._post("/api/jobs/create",
                                    {"company": "X", "status": "nope"}).status, 400)

    def test_jobs_status_filter(self) -> None:
        self._make_job(status="saved")
        self._make_job(status="applied")
        jobs = json.loads(api_app.route(self.ws, "/api/jobs", {"status": "applied"}).body)["jobs"]
        self.assertTrue(jobs)
        self.assertTrue(all(j["status"] == "applied" for j in jobs))

    def test_update_job_status(self) -> None:
        jid = self._make_job()
        resp = self._post("/api/jobs/update", {"id": jid, "status": "interview"})
        self.assertEqual(resp.status, 200)
        self.assertEqual(json.loads(resp.body)["updated"], 1)
        conn = self.ws.connect()
        try:
            self.assertEqual(repo.get_job(conn, jid)["status"], "interview")
        finally:
            conn.close()

    def test_update_job_unknown_404(self) -> None:
        self.assertEqual(self._post("/api/jobs/update", {"id": 99999, "status": "applied"}).status, 404)

    def test_update_job_bad_id_400(self) -> None:
        self.assertEqual(self._post("/api/jobs/update", {"status": "applied"}).status, 400)

    def test_update_job_invalid_status_400(self) -> None:
        jid = self._make_job()
        self.assertEqual(self._post("/api/jobs/update", {"id": jid, "status": "nope"}).status, 400)

    def test_delete_job(self) -> None:
        jid = self._make_job()
        resp = self._post("/api/jobs/delete", {"id": jid})
        self.assertEqual(resp.status, 200)
        self.assertEqual(json.loads(resp.body)["deleted"], 1)
        conn = self.ws.connect()
        try:
            self.assertIsNone(repo.get_job(conn, jid))
        finally:
            conn.close()

    def test_delete_job_unknown_404(self) -> None:
        self.assertEqual(self._post("/api/jobs/delete", {"id": 99999}).status, 404)

    def test_interview_grounded_with_notes(self) -> None:
        jid = self._make_job(notes="We use Python, FastAPI and SQLite. Expect system design.")
        resp = api_app.route(self.ws, "/api/jobs/interview", {"id": str(jid)})
        self.assertEqual(resp.status, 200)
        b = json.loads(resp.body)
        self.assertTrue(b["grounded"])
        self.assertTrue(b["sources"])
        self.assertTrue(b["text"])

    def test_interview_declines_without_notes(self) -> None:
        jid = self._make_job(notes=None)
        resp = api_app.route(self.ws, "/api/jobs/interview", {"id": str(jid)})
        self.assertEqual(resp.status, 200)
        self.assertFalse(json.loads(resp.body)["grounded"])

    def test_interview_clamps_n(self) -> None:
        jid = self._make_job(notes="python sql")
        resp = api_app.route(self.ws, "/api/jobs/interview", {"id": str(jid), "n": "999"})
        self.assertEqual(resp.status, 200)
        self.assertEqual(json.loads(resp.body)["n"], 15)

    def test_interview_unknown_id_404(self) -> None:
        self.assertEqual(api_app.route(self.ws, "/api/jobs/interview", {"id": "99999"}).status, 404)

    def test_interview_bad_id_400(self) -> None:
        self.assertEqual(api_app.route(self.ws, "/api/jobs/interview", {}).status, 400)
        self.assertEqual(api_app.route(self.ws, "/api/jobs/interview", {"id": "x"}).status, 400)

    def test_cv_against_target_text(self) -> None:
        resp = self._post("/api/cv", {"cv_text": "I know python and sql",
                                      "target_text": "python sql kubernetes"})
        self.assertEqual(resp.status, 200)
        b = json.loads(resp.body)
        self.assertIn("python", b["matched"])
        self.assertIn("kubernetes", b["missing"])
        self.assertGreaterEqual(b["coverage"], 0.0)
        self.assertLessEqual(b["coverage"], 1.0)

    def test_cv_against_job_notes(self) -> None:
        jid = self._make_job(notes="python sql docker")
        resp = self._post("/api/cv", {"cv_text": "python developer", "job_id": jid})
        self.assertEqual(resp.status, 200)
        self.assertIn("python", json.loads(resp.body)["matched"])

    def test_cv_missing_text_400(self) -> None:
        self.assertEqual(self._post("/api/cv", {"target_text": "python"}).status, 400)
        self.assertEqual(self._post("/api/cv", {"cv_text": "  ", "target_text": "python"}).status, 400)

    def test_cv_no_target_400(self) -> None:
        self.assertEqual(self._post("/api/cv", {"cv_text": "python dev"}).status, 400)

    def test_cv_unknown_job_404(self) -> None:
        self.assertEqual(self._post("/api/cv", {"cv_text": "x", "job_id": 99999}).status, 404)


class TestServeCommand(unittest.TestCase):
    def test_serve_is_registered(self) -> None:
        from devos.commands import COMMANDS
        names = {cls.name for cls in COMMANDS}
        self.assertIn("serve", names)

    def test_serve_pre_init_message_does_not_block(self) -> None:
        import io
        from contextlib import redirect_stdout
        from devos.cli import main
        prev = os.environ.get("DEVOS_HOME")
        tmp = tempfile.TemporaryDirectory()
        os.environ["DEVOS_HOME"] = tmp.name  # fresh, NOT initialized
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(["serve"])
            self.assertEqual(code, 0)
            self.assertIn("init", buf.getvalue().lower())
        finally:
            if prev is None:
                os.environ.pop("DEVOS_HOME", None)
            else:
                os.environ["DEVOS_HOME"] = prev
            tmp.cleanup()


class _LiveServerMixin(ApiTestCase):
    """Spin up a real loopback server for the duration of a test."""

    def _start(self):
        from devos.api import server as api_server
        srv = api_server.create_server("127.0.0.1", 0)
        port = srv.server_address[1]
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        self.addCleanup(th.join, 5)
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        return srv, port

    def _post(self, port, path, body, *, token=None, origin=None,
              content_type="application/json"):
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method="POST")
        if content_type is not None:
            req.add_header("Content-Type", content_type)
        if token is not None:
            req.add_header("X-DevOS-Token", token)
        if origin is not None:
            req.add_header("Origin", origin)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, None
        except (urllib.error.URLError, ConnectionError, OSError):
            # Server rejected + closed before we finished sending (e.g. oversized body):
            # a connection-level abort is also a valid "rejected" outcome.
            return -1, None


class TestLiveServer(_LiveServerMixin):
    def test_live_overview_and_index(self) -> None:
        srv, port = self._start()
        self.assertEqual(srv.server_address[0], "127.0.0.1")  # loopback only
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/overview", timeout=5) as r:
            self.assertEqual(r.status, 200)
            self.assertIn("task_counts", json.loads(r.read()))
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as r:
            self.assertEqual(r.status, 200)


class TestLiveSecurity(_LiveServerMixin):
    def _token(self, port) -> str:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/session", timeout=5) as r:
            return json.loads(r.read())["token"]

    def test_session_returns_token(self) -> None:
        _, port = self._start()
        self.assertTrue(self._token(port))

    def test_post_without_token_403(self) -> None:
        _, port = self._start()
        status, _ = self._post(port, "/api/tasks/create", {"title": "x"})
        self.assertEqual(status, 403)

    def test_post_wrong_token_403(self) -> None:
        _, port = self._start()
        status, _ = self._post(port, "/api/tasks/create", {"title": "x"}, token="nope")
        self.assertEqual(status, 403)

    def test_post_with_token_creates(self) -> None:
        _, port = self._start()
        status, body = self._post(port, "/api/tasks/create",
                                  {"title": "Live task"}, token=self._token(port))
        self.assertEqual(status, 201)
        self.assertIn("id", body)

    def test_post_bad_origin_403(self) -> None:
        _, port = self._start()
        status, _ = self._post(port, "/api/tasks/create", {"title": "x"},
                               token=self._token(port), origin="http://evil.example")
        self.assertEqual(status, 403)

    def test_post_non_json_415(self) -> None:
        _, port = self._start()
        status, _ = self._post(port, "/api/tasks/create", {"title": "x"},
                               token=self._token(port), content_type="text/plain")
        self.assertEqual(status, 415)

    def test_post_oversized_413(self) -> None:
        _, port = self._start()
        big = {"title": "x", "notes": "y" * (65 * 1024)}
        status, _ = self._post(port, "/api/tasks/create", big, token=self._token(port))
        # Oversized requests are rejected: a clean 413, or a connection abort because the
        # server closes without draining the oversized body (both mean "not processed").
        self.assertIn(status, (413, -1))

    def test_get_still_works(self) -> None:
        _, port = self._start()
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/overview", timeout=5) as r:
            self.assertEqual(r.status, 200)

    def test_scan_without_token_403(self) -> None:
        _, port = self._start()
        status, _ = self._post(port, "/api/projects/scan", {"path": "."})
        self.assertEqual(status, 403)

    def test_debug_without_token_403(self) -> None:
        _, port = self._start()
        status, _ = self._post(port, "/api/debug", {"trace": "ValueError: x"})
        self.assertEqual(status, 403)

    def test_settings_post_without_token_403(self) -> None:
        _, port = self._start()
        status, _ = self._post(port, "/api/settings", {"ai_provider": "mock"})
        self.assertEqual(status, 403)

    def test_grade_without_token_403(self) -> None:
        _, port = self._start()
        status, _ = self._post(port, "/api/grade", {"target": "main", "answer": "x"})
        self.assertEqual(status, 403)

    def test_task_delete_without_token_403(self) -> None:
        _, port = self._start()
        status, _ = self._post(port, "/api/tasks/delete", {"id": 1})
        self.assertEqual(status, 403)

    def test_project_delete_without_token_403(self) -> None:
        _, port = self._start()
        status, _ = self._post(port, "/api/projects/delete", {"id": 1})
        self.assertEqual(status, 403)

    def test_job_create_without_token_403(self) -> None:
        _, port = self._start()
        status, _ = self._post(port, "/api/jobs/create", {"company": "X"})
        self.assertEqual(status, 403)

    def test_cv_without_token_403(self) -> None:
        _, port = self._start()
        status, _ = self._post(port, "/api/cv", {"cv_text": "x", "target_text": "y"})
        self.assertEqual(status, 403)
