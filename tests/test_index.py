"""Phase 3 — indexing & search tests (TDD, stdlib unittest)."""
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
from devos.storage import db, repo


def _write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


class TestSchemaV2(unittest.TestCase):
    def test_files_has_indexed_hash_at_latest_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dbp = Path(tmp) / "devos.db"
            conn = db.initialize(dbp)
            try:
                self.assertEqual(db.schema_version(conn), db.SCHEMA_VERSION)
                cols = {r["name"] for r in conn.execute("PRAGMA table_info(files);")}
                self.assertIn("indexed_hash", cols)
            finally:
                conn.close()

    def test_upgrade_from_v1_runs_all_migrations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dbp = Path(tmp) / "devos.db"
            # Simulate a legacy v1 DB: real v1 had files + tasks tables (see schema.sql).
            conn = db.connect(dbp)
            conn.executescript(
                "CREATE TABLE files (id INTEGER PRIMARY KEY, project_id INTEGER, "
                "rel_path TEXT, content_hash TEXT);"
                "CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT, status TEXT);"
            )
            conn.execute("PRAGMA user_version = 1;")
            conn.commit()
            conn.close()

            conn = db.initialize(dbp)  # should migrate v1 -> latest
            try:
                self.assertEqual(db.schema_version(conn), db.SCHEMA_VERSION)
                fcols = {r["name"] for r in conn.execute("PRAGMA table_info(files);")}
                tcols = {r["name"] for r in conn.execute("PRAGMA table_info(tasks);")}
                self.assertIn("indexed_hash", fcols)
                self.assertIn("priority", tcols)
            finally:
                conn.close()


class TestChunking(unittest.TestCase):
    def test_splits_into_line_windows(self) -> None:
        text = "\n".join(f"line{i}" for i in range(1, 121))  # 120 lines
        chunks = index_mod.chunk_text(text, max_lines=50)
        self.assertEqual(len(chunks), 3)
        self.assertEqual((chunks[0].start_line, chunks[0].end_line), (1, 50))
        self.assertEqual((chunks[1].start_line, chunks[1].end_line), (51, 100))
        self.assertEqual((chunks[2].start_line, chunks[2].end_line), (101, 120))
        self.assertTrue(chunks[0].content.startswith("line1"))
        self.assertIn("line50", chunks[0].content)

    def test_empty_text_yields_no_chunks(self) -> None:
        self.assertEqual(index_mod.chunk_text(""), [])
        self.assertEqual(index_mod.chunk_text("   \n  \n"), [])

    def test_single_short_file_is_one_chunk(self) -> None:
        chunks = index_mod.chunk_text("a\nb\nc", max_lines=50)
        self.assertEqual(len(chunks), 1)
        self.assertEqual((chunks[0].start_line, chunks[0].end_line), (1, 3))


class TestRepoIndexHelpers(unittest.TestCase):
    def _conn(self, tmp: str):
        return db.initialize(Path(tmp) / "devos.db")

    def test_insert_and_count_and_delete_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = self._conn(tmp)
            try:
                pid = repo.upsert_project(conn, "/x", "x")
                repo.upsert_file(conn, pid, "a.py", "python", "backend", 3, "h1")
                fid = conn.execute(
                    "SELECT id FROM files WHERE project_id=? AND rel_path='a.py';", (pid,)
                ).fetchone()["id"]

                cid = repo.insert_chunk(conn, fid, 1, 2, "backend,python", "ch1", "print(1)")
                self.assertEqual(repo.file_chunk_count(conn, fid), 1)
                self.assertEqual(
                    conn.execute("SELECT content FROM chunks_fts WHERE chunk_id=?;",
                                 (cid,)).fetchone()["content"],
                    "print(1)",
                )

                repo.delete_chunks_for_file(conn, fid)
                self.assertEqual(repo.file_chunk_count(conn, fid), 0)
                self.assertIsNone(
                    conn.execute("SELECT 1 FROM chunks_fts WHERE chunk_id=?;",
                                 (cid,)).fetchone()
                )
            finally:
                conn.close()


class IndexTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._prev = os.environ.get("DEVOS_HOME")
        self._home = tempfile.TemporaryDirectory()
        os.environ["DEVOS_HOME"] = self._home.name
        self.ws = Workspace.load()
        self.ws.initialize().close()
        self._proj = tempfile.TemporaryDirectory()
        self.root = Path(self._proj.name)
        _write(self.root, "server/app.py", "\n".join(f"row{i}" for i in range(60)))
        _write(self.root, "src/util.ts", "export const token = 'abc';")

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("DEVOS_HOME", None)
        else:
            os.environ["DEVOS_HOME"] = self._prev
        self._home.cleanup()
        self._proj.cleanup()


class TestIndexProject(IndexTestCase):
    def test_first_index_creates_chunks(self) -> None:
        conn = self.ws.connect()
        try:
            pid = ingest.scan_project(conn, self.root).project_id
            result = index_mod.index_project(conn, pid)
            self.assertGreaterEqual(result.indexed_files, 2)
            chunks, files = repo.chunk_stats(conn, pid)
            self.assertGreater(chunks, 0)
            self.assertGreaterEqual(files, 2)
        finally:
            conn.close()

    def test_reindex_unchanged_is_noop(self) -> None:
        conn = self.ws.connect()
        try:
            pid = ingest.scan_project(conn, self.root).project_id
            index_mod.index_project(conn, pid)
            chunks_before, _ = repo.chunk_stats(conn, pid)
            result = index_mod.index_project(conn, pid)
            self.assertEqual(result.indexed_files, 0)
            self.assertEqual(result.unchanged_files, 2)
            chunks_after, _ = repo.chunk_stats(conn, pid)
            self.assertEqual(chunks_after, chunks_before)
        finally:
            conn.close()

    def test_empty_file_is_unchanged_on_reindex(self) -> None:
        # An empty file yields no chunks; it must still count as "unchanged" on a
        # second index rather than being re-processed every run.
        _write(self.root, "pkg/__init__.py", "")
        conn = self.ws.connect()
        try:
            pid = ingest.scan_project(conn, self.root).project_id
            index_mod.index_project(conn, pid)
            result = index_mod.index_project(conn, pid)
            self.assertEqual(result.indexed_files, 0)
            self.assertEqual(result.unchanged_files, 3)  # app.py, util.ts, __init__.py
        finally:
            conn.close()

    def test_modified_file_is_reindexed(self) -> None:
        conn = self.ws.connect()
        try:
            pid = ingest.scan_project(conn, self.root).project_id
            index_mod.index_project(conn, pid)
            _write(self.root, "src/util.ts", "export const token = 'changed';\nconst y = 2;")
            ingest.scan_project(conn, self.root)
            result = index_mod.index_project(conn, pid)
            self.assertEqual(result.indexed_files, 1)
            self.assertEqual(result.unchanged_files, 1)
        finally:
            conn.close()

    def test_deleted_file_chunks_are_removed(self) -> None:
        conn = self.ws.connect()
        try:
            pid = ingest.scan_project(conn, self.root).project_id
            index_mod.index_project(conn, pid)
            (self.root / "src/util.ts").unlink()
            ingest.scan_project(conn, self.root)  # prunes the file row (chunks cascade)
            index_mod.index_project(conn, pid)     # reconcile_fts cleans fts orphans
            orphans = conn.execute(
                "SELECT COUNT(*) FROM chunks_fts WHERE chunk_id NOT IN (SELECT id FROM chunks);"
            ).fetchone()[0]
            self.assertEqual(orphans, 0)
        finally:
            conn.close()


class TestMatchQuery(unittest.TestCase):
    def test_tokens_are_quoted_and_anded(self) -> None:
        self.assertEqual(index_mod.build_match_query("auth login"), '"auth" "login"')

    def test_special_chars_are_escaped_not_injected(self) -> None:
        q = index_mod.build_match_query('def(x): "y"')
        self.assertNotIn('("', q)
        self.assertTrue(q.startswith('"'))

    def test_empty_query_is_empty(self) -> None:
        self.assertEqual(index_mod.build_match_query("   "), "")


class TestSearch(IndexTestCase):
    def setUp(self) -> None:
        super().setUp()
        _write(self.root, "src/auth/login.py",
               "def authenticate(token):\n    return verify(token)")
        conn = self.ws.connect()
        try:
            pid = ingest.scan_project(conn, self.root).project_id
            index_mod.index_project(conn, pid)
        finally:
            conn.close()

    def test_search_finds_token_with_location(self) -> None:
        conn = self.ws.connect()
        try:
            hits = index_mod.search(conn, "authenticate")
            self.assertTrue(hits)
            top = hits[0]
            self.assertEqual(top.rel_path, "src/auth/login.py")
            self.assertGreaterEqual(top.start_line, 1)
            self.assertIn("authenticate", top.snippet.lower())
        finally:
            conn.close()

    def test_no_match_returns_empty(self) -> None:
        conn = self.ws.connect()
        try:
            self.assertEqual(index_mod.search(conn, "zzz_no_such_token_qqq"), [])
        finally:
            conn.close()

    def test_special_char_query_does_not_raise(self) -> None:
        conn = self.ws.connect()
        try:
            index_mod.search(conn, 'def(token):')  # must not raise sqlite errors
        finally:
            conn.close()


class TestIndexCli(IndexTestCase):
    def _run(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_index_command_reports_chunks(self) -> None:
        code, out = self._run("index", str(self.root))
        self.assertEqual(code, 0)
        self.assertIn("chunk", out.lower())


class TestSearchCli(IndexTestCase):
    def _run(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_search_after_index(self) -> None:
        _write(self.root, "src/auth/login.py", "def authenticate(token):\n    return token")
        self._run("index", str(self.root))
        code, out = self._run("search", "authenticate")
        self.assertEqual(code, 0)
        self.assertIn("login.py", out)

    def test_search_no_results_message(self) -> None:
        self._run("index", str(self.root))
        code, out = self._run("search", "zzz_nope_qqq")
        self.assertEqual(code, 0)
        self.assertIn("No matches", out)
