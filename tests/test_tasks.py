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
