"""Phase 6 — Memory + Recall tests (TDD, stdlib unittest)."""
from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from devos.cli import main
from devos.core.workspace import Workspace
from devos.modules import index as index_mod
from devos.modules import ingest
from devos.modules import recall as recall_mod
from devos.storage import repo


def _write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


class RecallTestCase(unittest.TestCase):
    """Isolated home + an indexed sample project (so code recall has something)."""

    def setUp(self) -> None:
        self._prev = os.environ.get("DEVOS_HOME")
        self._home = tempfile.TemporaryDirectory()
        os.environ["DEVOS_HOME"] = self._home.name
        self.ws = Workspace.load()
        self.ws.initialize().close()
        self._proj = tempfile.TemporaryDirectory()
        self.root = Path(self._proj.name)
        _write(self.root, "src/provider.py",
               "class ClaudeProvider:\n    # wires the anthropic claude api\n    def complete(self): ...")
        conn = self.ws.connect()
        try:
            self.pid = ingest.scan_project(conn, self.root, name="demo").project_id
            index_mod.index_project(conn, self.pid)
        finally:
            conn.close()

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("DEVOS_HOME", None)
        else:
            os.environ["DEVOS_HOME"] = self._prev
        self._home.cleanup()
        self._proj.cleanup()


class TestMemoryRepo(RecallTestCase):
    def test_create_get_and_idempotent(self) -> None:
        conn = self.ws.connect()
        try:
            mid = repo.create_memory(conn, None, kind="decision",
                                     title="Use FTS5", body="local-first search", tags="search")
            row = repo.get_memory(conn, mid)
            self.assertEqual(row["title"], "Use FTS5")
            self.assertEqual(row["kind"], "decision")
            # exact duplicate returns the same id (idempotent), no second row
            mid2 = repo.create_memory(conn, None, kind="decision",
                                      title="Use FTS5", body="local-first search", tags="x")
            self.assertEqual(mid2, mid)
            self.assertEqual(len(repo.list_memory(conn)), 1)
        finally:
            conn.close()

    def test_list_and_delete(self) -> None:
        conn = self.ws.connect()
        try:
            a = repo.create_memory(conn, None, kind="note", title="A", body="aaa")
            repo.create_memory(conn, None, kind="note", title="B", body="bbb")
            self.assertEqual(len(repo.list_memory(conn)), 2)
            self.assertEqual(repo.delete_memory(conn, a), 1)
            self.assertEqual(len(repo.list_memory(conn)), 1)
        finally:
            conn.close()

    def test_search_memory_like(self) -> None:
        conn = self.ws.connect()
        try:
            repo.create_memory(conn, None, kind="decision",
                               title="Provider abstraction", body="swap claude later", tags="ai")
            repo.create_memory(conn, None, kind="note", title="Other", body="nothing relevant")
            hits = repo.search_memory(conn, "claude", limit=10)
            self.assertEqual([m["title"] for m in hits], ["Provider abstraction"])
        finally:
            conn.close()


class TestRecallModule(RecallTestCase):
    def test_recall_spans_memory_tasks_and_code(self) -> None:
        conn = self.ws.connect()
        try:
            repo.create_memory(conn, None, kind="decision",
                               title="Claude provider plan", body="wire claude behind interface")
            repo.create_task(conn, None, "Implement Claude provider", kind="feature",
                             status="todo", priority="high")
            result = recall_mod.recall(conn, "claude")
            self.assertTrue(any("Claude" in m["title"] for m in result.memories))
            self.assertTrue(any("Claude" in t["title"] for t in result.tasks))
            self.assertTrue(any(c.rel_path == "src/provider.py" for c in result.code))
        finally:
            conn.close()

    def test_recall_empty_query_lists_recent(self) -> None:
        conn = self.ws.connect()
        try:
            repo.create_memory(conn, None, kind="note", title="Recent note", body="x")
            repo.create_task(conn, None, "Recent task", kind="task", status="todo", priority="low")
            result = recall_mod.recall(conn, "")
            self.assertTrue(result.memories)
            self.assertTrue(result.tasks)
            self.assertEqual(result.code, [])  # no code without a query
        finally:
            conn.close()

    def test_recall_no_matches_is_empty(self) -> None:
        conn = self.ws.connect()
        try:
            result = recall_mod.recall(conn, "zzzqqq_absent_term_xyz")
            self.assertEqual(result.memories, [])
            self.assertEqual(result.tasks, [])
            self.assertEqual(result.code, [])
        finally:
            conn.close()


class TestRememberRecallCli(RecallTestCase):
    def _run(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_remember_creates_memory(self) -> None:
        code, out = self._run("remember", "Use", "FTS5", "for", "search",
                              "--kind", "decision", "--tags", "search,sqlite")
        self.assertEqual(code, 0)
        conn = self.ws.connect()
        try:
            mems = repo.list_memory(conn)
            self.assertEqual(len(mems), 1)
            self.assertEqual(mems[0]["title"], "Use FTS5 for search")
            self.assertEqual(mems[0]["kind"], "decision")
        finally:
            conn.close()

    def test_recall_groups_results(self) -> None:
        conn = self.ws.connect()
        try:
            repo.create_memory(conn, None, kind="decision",
                               title="Claude provider plan", body="wire claude later")
            repo.create_task(conn, None, "Implement Claude provider", kind="feature",
                             status="todo", priority="high")
        finally:
            conn.close()
        code, out = self._run("recall", "claude")
        self.assertEqual(code, 0)
        self.assertIn("Memory", out)
        self.assertIn("Tasks", out)
        self.assertIn("Code", out)
        self.assertIn("src/provider.py", out)

    def test_recall_nothing_found(self) -> None:
        code, out = self._run("recall", "zzzqqq_absent_term_xyz")
        self.assertEqual(code, 0)
        self.assertIn("Nothing", out)
