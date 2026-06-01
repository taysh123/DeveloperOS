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


class TestCareerModule(CareerTestCase):
    def test_analyze_cv_matched_missing_coverage(self) -> None:
        cv = "Experienced Python developer with REST APIs and Docker."
        target = "Looking for Python engineer with SQLite and REST experience."
        analysis = career_mod.analyze_cv(cv, target)
        self.assertIn("python", analysis.matched)
        self.assertIn("rest", analysis.matched)
        self.assertIn("sqlite", analysis.missing)
        self.assertGreater(analysis.coverage, 0.0)
        self.assertLessEqual(analysis.coverage, 1.0)

    def test_analyze_cv_empty_target(self) -> None:
        analysis = career_mod.analyze_cv("python developer", "")
        self.assertEqual(analysis.matched, set())
        self.assertEqual(analysis.coverage, 0.0)

    def test_interview_prep_grounded(self) -> None:
        conn = self.ws.connect()
        try:
            jid = repo.create_job(conn, "Acme", role="Backend Eng",
                                  notes="python, sqlite, rest api design, testing")
            prep = career_mod.interview_prep(conn, jid, provider=MockAIProvider(), n=3)
            self.assertTrue(prep.grounded)
            self.assertTrue(prep.sources)
            self.assertIn("Acme", prep.text)  # mock echoes the job context
        finally:
            conn.close()

    def test_interview_prep_declines_when_no_notes(self) -> None:
        class BoomProvider(MockAIProvider):
            def complete(self, *a, **k):
                raise AssertionError("provider must not be called without job notes")
        conn = self.ws.connect()
        try:
            jid = repo.create_job(conn, "NoNotes", notes=None)
            prep = career_mod.interview_prep(conn, jid, provider=BoomProvider())
            self.assertFalse(prep.grounded)
        finally:
            conn.close()

    def test_interview_prep_unknown_job_declines(self) -> None:
        conn = self.ws.connect()
        try:
            prep = career_mod.interview_prep(conn, 9999, provider=MockAIProvider())
            self.assertFalse(prep.grounded)
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


class TestCvInterviewCli(CareerTestCase):
    def _run(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_cv_against_job(self) -> None:
        conn = self.ws.connect()
        try:
            jid = repo.create_job(conn, "Acme", role="Backend",
                                  notes="python sqlite rest api docker kubernetes")
        finally:
            conn.close()
        cv = Path(self._home.name) / "cv.txt"
        cv.write_text("Python developer with REST APIs and SQLite.", encoding="utf-8")
        code, out = self._run("cv", str(cv), "--job", str(jid))
        self.assertEqual(code, 0)
        self.assertIn("overage", out)       # "Coverage"
        self.assertIn("python", out.lower())
        self.assertIn("kubernetes", out.lower())  # a missing keyword

    def test_cv_missing_file_errors(self) -> None:
        code, out = self._run("cv", str(Path(self._home.name) / "nope.txt"))
        self.assertEqual(code, 1)
        self.assertIn("cannot read", out.lower())

    def test_interview_grounded(self) -> None:
        conn = self.ws.connect()
        try:
            jid = repo.create_job(conn, "Acme", role="Backend",
                                  notes="python, sqlite, rest, testing")
        finally:
            conn.close()
        code, out = self._run("interview", str(jid), "--n", "3")
        self.assertEqual(code, 0)
        self.assertIn("Acme", out)

    def test_interview_unknown_declines(self) -> None:
        code, out = self._run("interview", "9999")
        self.assertEqual(code, 0)
        self.assertIn("Not enough", out)
