"""Phase 6 — Task Manager tests (TDD, stdlib unittest)."""
from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from devos.cli import main
from devos.core.workspace import Workspace
from devos.storage import db, repo


class TestSchemaV3(unittest.TestCase):
    def test_fresh_db_has_priority_and_version_3(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = db.initialize(Path(tmp) / "devos.db")
            try:
                self.assertEqual(db.schema_version(conn), 3)
                cols = {r["name"] for r in conn.execute("PRAGMA table_info(tasks);")}
                self.assertIn("priority", cols)
            finally:
                conn.close()

    def test_upgrade_v2_to_v3_adds_priority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dbp = Path(tmp) / "devos.db"
            conn = db.connect(dbp)
            conn.executescript(
                "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT);"
                "CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT, status TEXT);"
            )
            conn.execute("PRAGMA user_version = 2;")
            conn.commit()
            conn.close()

            conn = db.initialize(dbp)
            try:
                self.assertEqual(db.schema_version(conn), 3)
                cols = {r["name"] for r in conn.execute("PRAGMA table_info(tasks);")}
                self.assertIn("priority", cols)
            finally:
                conn.close()


class TaskTestCase(unittest.TestCase):
    """Isolated home + initialized DB."""

    def setUp(self) -> None:
        self._prev = os.environ.get("DEVOS_HOME")
        self._home = tempfile.TemporaryDirectory()
        os.environ["DEVOS_HOME"] = self._home.name
        self.ws = Workspace.load()
        self.ws.initialize().close()

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("DEVOS_HOME", None)
        else:
            os.environ["DEVOS_HOME"] = self._prev
        self._home.cleanup()


class TestTaskRepo(TaskTestCase):
    def test_create_and_get(self) -> None:
        conn = self.ws.connect()
        try:
            tid = repo.create_task(conn, None, "Fix login", kind="bug",
                                   status="todo", priority="high", milestone="M1", notes="n")
            row = repo.get_task(conn, tid)
            self.assertEqual(row["title"], "Fix login")
            self.assertEqual(row["kind"], "bug")
            self.assertEqual(row["priority"], "high")
            self.assertEqual(row["status"], "todo")
        finally:
            conn.close()

    def test_list_with_filters(self) -> None:
        conn = self.ws.connect()
        try:
            repo.create_task(conn, None, "A", kind="task", status="todo", priority="medium")
            repo.create_task(conn, None, "B", kind="bug", status="done", priority="low")
            todos = repo.list_tasks(conn, status="todo")
            self.assertEqual([t["title"] for t in todos], ["A"])
            bugs = repo.list_tasks(conn, kind="bug")
            self.assertEqual([t["title"] for t in bugs], ["B"])
        finally:
            conn.close()

    def test_update_sets_fields_and_timestamp(self) -> None:
        conn = self.ws.connect()
        try:
            tid = repo.create_task(conn, None, "T", kind="task", status="todo", priority="medium")
            before = repo.get_task(conn, tid)["updated_at"]
            repo.update_task(conn, tid, status="in_progress", priority="high", notes="started")
            row = repo.get_task(conn, tid)
            self.assertEqual(row["status"], "in_progress")
            self.assertEqual(row["priority"], "high")
            self.assertEqual(row["notes"], "started")
            self.assertGreaterEqual(row["updated_at"], before)
        finally:
            conn.close()

    def test_delete(self) -> None:
        conn = self.ws.connect()
        try:
            tid = repo.create_task(conn, None, "T", kind="task", status="todo", priority="medium")
            self.assertEqual(repo.delete_task(conn, tid), 1)
            self.assertIsNone(repo.get_task(conn, tid))
        finally:
            conn.close()

    def test_search_tasks_like(self) -> None:
        conn = self.ws.connect()
        try:
            repo.create_task(conn, None, "Wire Claude provider", kind="feature",
                             status="todo", priority="high", notes="behind interface")
            repo.create_task(conn, None, "Unrelated", kind="task", status="todo", priority="low")
            hits = repo.search_tasks(conn, "claude", limit=10)
            self.assertEqual([t["title"] for t in hits], ["Wire Claude provider"])
        finally:
            conn.close()
