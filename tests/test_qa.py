"""Phase 4 — Q&A & project understanding tests (TDD, stdlib unittest)."""
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
from devos.modules import qa
from devos.providers.ai import MockAIProvider
from devos.storage import db, repo


def _write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


class QaTestCase(unittest.TestCase):
    """Isolated home + an indexed sample project."""

    def setUp(self) -> None:
        self._prev = os.environ.get("DEVOS_HOME")
        self._home = tempfile.TemporaryDirectory()
        os.environ["DEVOS_HOME"] = self._home.name
        self.ws = Workspace.load()
        self.ws.initialize().close()
        self._proj = tempfile.TemporaryDirectory()
        self.root = Path(self._proj.name)
        _write(self.root, "src/auth/login.py",
               "def authenticate(token):\n    # verify the session token\n    return verify(token)")
        _write(self.root, "src/util.ts", "export const greeting = 'hello world';")
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


class TestRepoRetrievalHelpers(QaTestCase):
    def test_get_chunk_content_roundtrip(self) -> None:
        conn = self.ws.connect()
        try:
            hits = index_mod.search(conn, "authenticate")
            self.assertTrue(hits)
            content = repo.get_chunk_content(conn, hits[0].chunk_id)
            self.assertIn("authenticate", content)
        finally:
            conn.close()

    def test_get_file_chunks_ordered_with_content(self) -> None:
        conn = self.ws.connect()
        try:
            rows = repo.get_file_chunks(conn, self.pid, "src/auth/login.py")
            self.assertTrue(rows)
            self.assertIn("authenticate", rows[0]["content"])
        finally:
            conn.close()

    def test_find_project_for_path(self) -> None:
        conn = self.ws.connect()
        try:
            row = repo.find_project_for_path(conn, str(self.root / "src" / "util.ts"))
            self.assertIsNotNone(row)
            self.assertEqual(row["id"], self.pid)
            self.assertIsNone(repo.find_project_for_path(conn, "/nowhere/else/x.py"))
        finally:
            conn.close()

    def test_top_files_by_chunk_count(self) -> None:
        conn = self.ws.connect()
        try:
            files = repo.top_files(conn, self.pid, 5)
            self.assertTrue(files)
            self.assertIn("rel_path", files[0].keys())
            self.assertIn("chunk_count", files[0].keys())
        finally:
            conn.close()


class TestOrQuery(unittest.TestCase):
    def test_or_mode_joins_with_or(self) -> None:
        self.assertEqual(index_mod.build_match_query("auth login", op="OR"),
                         '"auth" OR "login"')

    def test_and_mode_is_default(self) -> None:
        self.assertEqual(index_mod.build_match_query("auth login"), '"auth" "login"')


class TestOrSearch(QaTestCase):
    def test_or_search_matches_any_term(self) -> None:
        conn = self.ws.connect()
        try:
            # 'authenticate' and 'greeting' live in different files; AND finds neither
            and_hits = index_mod.search(conn, "authenticate greeting")
            or_hits = index_mod.search(conn, "authenticate greeting", op="OR")
            self.assertEqual(and_hits, [])
            self.assertGreaterEqual(len(or_hits), 2)
        finally:
            conn.close()
