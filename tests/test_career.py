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


class TestJobRepo(CareerTestCase):
    def test_create_get(self) -> None:
        conn = self.ws.connect()
        try:
            jid = repo.create_job(conn, "Acme", role="Backend Eng", url="http://x",
                                  status="applied", notes="python sqlite rest")
            row = repo.get_job(conn, jid)
            self.assertEqual(row["company"], "Acme")
            self.assertEqual(row["role"], "Backend Eng")
            self.assertEqual(row["status"], "applied")
        finally:
            conn.close()

    def test_list_filter_update_delete(self) -> None:
        conn = self.ws.connect()
        try:
            a = repo.create_job(conn, "Acme", status="applied")
            repo.create_job(conn, "Globex", status="saved")
            self.assertEqual([j["company"] for j in repo.list_jobs(conn, status="applied")], ["Acme"])
            repo.update_job(conn, a, status="interview", notes="round 1")
            self.assertEqual(repo.get_job(conn, a)["status"], "interview")
            self.assertEqual(repo.delete_job(conn, a), 1)
            self.assertIsNone(repo.get_job(conn, a))
        finally:
            conn.close()


class TestJobCli(CareerTestCase):
    def _run(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_add_and_list(self) -> None:
        code, out = self._run("job", "add", "Acme", "--role", "Backend Eng",
                              "--status", "applied", "--notes", "python sqlite")
        self.assertEqual(code, 0)
        code, out = self._run("job", "list")
        self.assertEqual(code, 0)
        self.assertIn("Acme", out)
        self.assertIn("applied", out)

    def test_set_and_show_and_rm(self) -> None:
        conn = self.ws.connect()
        try:
            jid = repo.create_job(conn, "Globex", status="saved")
        finally:
            conn.close()
        code, out = self._run("job", "set", str(jid), "--status", "interview")
        self.assertEqual(code, 0)
        code, out = self._run("job", "show", str(jid))
        self.assertIn("Globex", out)
        self.assertIn("interview", out)
        code, out = self._run("job", "rm", str(jid))
        self.assertEqual(code, 0)

    def test_list_empty(self) -> None:
        code, out = self._run("job", "list")
        self.assertEqual(code, 0)
        self.assertIn("No job", out)
