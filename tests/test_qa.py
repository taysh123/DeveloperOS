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


class TestRetrieve(QaTestCase):
    def test_retrieve_returns_chunks_with_content_and_location(self) -> None:
        conn = self.ws.connect()
        try:
            chunks = qa.retrieve(conn, "how does authenticate work")
            self.assertTrue(chunks)
            top = chunks[0]
            self.assertIn("authenticate", top.content)
            self.assertEqual(top.rel_path, "src/auth/login.py")
            self.assertRegex(top.location, r"src/auth/login\.py:\d+-\d+")
        finally:
            conn.close()

    def test_retrieve_empty_when_no_match(self) -> None:
        conn = self.ws.connect()
        try:
            self.assertEqual(qa.retrieve(conn, "zzzqqq_nonexistent_term"), [])
        finally:
            conn.close()

    def test_question_terms_drops_stopwords(self) -> None:
        terms = qa.question_terms("How does the authentication flow work?")
        self.assertIn("authentication", terms)
        self.assertNotIn("how", terms)
        self.assertNotIn("the", terms)

    def test_assemble_context_tags_sources(self) -> None:
        conn = self.ws.connect()
        try:
            chunks = qa.retrieve(conn, "authenticate")
            ctx = qa.assemble_context(chunks)
            self.assertIn("src/auth/login.py", ctx)
            self.assertIn("[Source 1]", ctx)
        finally:
            conn.close()


class TestAnswer(QaTestCase):
    def test_answer_is_grounded_with_sources(self) -> None:
        conn = self.ws.connect()
        try:
            ans = qa.answer(conn, "how does authenticate work", provider=MockAIProvider())
            self.assertTrue(ans.grounded)
            self.assertTrue(ans.sources)
            self.assertEqual(ans.sources[0].rel_path, "src/auth/login.py")
            self.assertEqual(ans.provider, "mock")
        finally:
            conn.close()

    def test_answer_declines_when_no_context(self) -> None:
        conn = self.ws.connect()
        try:
            ans = qa.answer(conn, "zzzqqq_nonexistent_term", provider=MockAIProvider())
            self.assertFalse(ans.grounded)
            self.assertEqual(ans.sources, [])
            self.assertIn("don't have enough", ans.text)
        finally:
            conn.close()

    def test_answer_does_not_call_provider_when_empty(self) -> None:
        class BoomProvider(MockAIProvider):
            def complete(self, *a, **k):
                raise AssertionError("provider must not be called without context")
        conn = self.ws.connect()
        try:
            ans = qa.answer(conn, "zzzqqq_nonexistent_term", provider=BoomProvider())
            self.assertFalse(ans.grounded)
        finally:
            conn.close()


class TestExplain(QaTestCase):
    def test_explain_file_uses_its_chunks(self) -> None:
        conn = self.ws.connect()
        try:
            ans = qa.explain(conn, str(self.root / "src" / "auth" / "login.py"),
                             provider=MockAIProvider())
            self.assertTrue(ans.grounded)
            self.assertTrue(any(s.rel_path == "src/auth/login.py" for s in ans.sources))
        finally:
            conn.close()

    def test_explain_unknown_path_declines(self) -> None:
        conn = self.ws.connect()
        try:
            ans = qa.explain(conn, "/nowhere/x.py", provider=MockAIProvider())
            self.assertFalse(ans.grounded)
            self.assertIn("not", ans.text.lower())
        finally:
            conn.close()

    def test_explain_project_overview(self) -> None:
        conn = self.ws.connect()
        try:
            ans = qa.explain(conn, None, provider=MockAIProvider(), project="demo")
            self.assertTrue(ans.grounded)
            self.assertTrue(ans.sources)  # cites notable files
        finally:
            conn.close()


class TestAskCli(QaTestCase):
    def _run(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_ask_prints_answer_and_sources(self) -> None:
        code, out = self._run("ask", "how", "does", "authenticate", "work")
        self.assertEqual(code, 0)
        self.assertIn("Sources", out)
        self.assertIn("login.py", out)

    def test_ask_declines_without_context(self) -> None:
        code, out = self._run("ask", "zzzqqq_nonexistent_term")
        self.assertEqual(code, 0)
        self.assertIn("don't have enough", out)


class TestExplainCli(QaTestCase):
    def _run(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_explain_file(self) -> None:
        code, out = self._run("explain", str(self.root / "src" / "auth" / "login.py"))
        self.assertEqual(code, 0)
        self.assertIn("login.py", out)

    def test_explain_project_overview(self) -> None:
        code, out = self._run("explain", "--project", "demo")
        self.assertEqual(code, 0)
        self.assertIn("Sources", out)


class TestAndFirstRetrieval(unittest.TestCase):
    """Precision upgrade: AND-matching chunks beat single-term incidental matches."""

    def setUp(self) -> None:
        self._prev = os.environ.get("DEVOS_HOME")
        self._home = tempfile.TemporaryDirectory()
        os.environ["DEVOS_HOME"] = self._home.name
        ws = Workspace.load()
        ws.initialize().close()
        self._proj = tempfile.TemporaryDirectory()
        root = Path(self._proj.name)
        # One file matches BOTH terms; another matches only one (incidentally).
        (root / "auth_flow.py").write_text(
            "def login_session(user):\n    # token refresh handled here\n    return user\n",
            encoding="utf-8")
        (root / "unrelated.py").write_text(
            "def helper():\n    return 'token'  # token mentioned once, incidentally\n",
            encoding="utf-8")
        self.conn = ws.connect()
        pid = ingest.scan_project(self.conn, root, name="andtest").project_id
        index_mod.index_project(self.conn, pid)

    def tearDown(self) -> None:
        self.conn.close()
        if self._prev is None:
            os.environ.pop("DEVOS_HOME", None)
        else:
            os.environ["DEVOS_HOME"] = self._prev
        self._home.cleanup()
        self._proj.cleanup()

    def test_and_match_excludes_incidental_single_term_chunks(self) -> None:
        chunks = qa.retrieve(self.conn, "token refresh")
        self.assertTrue(chunks)
        paths = {c.rel_path for c in chunks}
        self.assertIn("auth_flow.py", paths)
        self.assertNotIn("unrelated.py", paths)  # OR alone would have included it

    def test_falls_back_to_or_when_and_finds_nothing(self) -> None:
        # "token zebra": no chunk has both, but "token" exists → OR fallback grounds it.
        chunks = qa.retrieve(self.conn, "token zebra")
        self.assertTrue(chunks)

    def test_still_declines_when_nothing_matches_at_all(self) -> None:
        self.assertEqual(qa.retrieve(self.conn, "qqzz xxyy"), [])
