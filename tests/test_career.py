"""Phase 9 (slice 4) — Career Assistant tests (TDD, stdlib unittest)."""
from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from devos.cli import main
from devos.core.workspace import Workspace
from devos.modules import career as career_mod
from devos.providers.ai import MockAIProvider
from devos.storage import db, repo


class TestSchemaV4(unittest.TestCase):
    def test_fresh_db_has_job_leads_and_version_4(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = db.initialize(Path(tmp) / "devos.db")
            try:
                self.assertEqual(db.schema_version(conn), 4)
                names = {r["name"] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table';")}
                self.assertIn("job_leads", names)
                self.assertIn("job_leads", db.COUNTED_TABLES)
            finally:
                conn.close()

    def test_upgrade_v3_to_v4_creates_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dbp = Path(tmp) / "devos.db"
            conn = db.connect(dbp)
            conn.executescript(
                "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT);"
            )
            conn.execute("PRAGMA user_version = 3;")
            conn.commit()
            conn.close()

            conn = db.initialize(dbp)
            try:
                self.assertEqual(db.schema_version(conn), 4)
                names = {r["name"] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table';")}
                self.assertIn("job_leads", names)
            finally:
                conn.close()


class CareerTestCase(unittest.TestCase):
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
