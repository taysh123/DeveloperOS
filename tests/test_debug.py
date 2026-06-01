"""Phase 5 — Debug Assistant tests (TDD, stdlib unittest)."""
from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from devos.cli import main
from devos.core.workspace import Workspace
from devos.modules import debug as debug_mod
from devos.modules import index as index_mod
from devos.modules import ingest
from devos.modules import trace as trace_mod
from devos.providers.ai import MockAIProvider
from devos.storage import repo


def _write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


PY_TRACE = '''Traceback (most recent call last):
  File "src/app.py", line 12, in handler
    return compute(value)
  File "src/calc.py", line 3, in compute
    return 1 / divisor
ZeroDivisionError: division by zero'''

NODE_TRACE = '''TypeError: Cannot read properties of undefined (reading 'id')
    at getUser (src/user.js:42:18)
    at Object.<anonymous> (src/index.js:7:1)
    at node:internal/modules/cjs/loader:1234:14'''


class TestTraceParsing(unittest.TestCase):
    def test_python_trace(self) -> None:
        parsed = trace_mod.parse_trace(PY_TRACE)
        self.assertEqual(parsed.language, "python")
        self.assertEqual(parsed.error_type, "ZeroDivisionError")
        self.assertIn("division by zero", parsed.error_message)
        files = [(f.file, f.line, f.func) for f in parsed.frames]
        self.assertIn(("src/app.py", 12, "handler"), files)
        self.assertIn(("src/calc.py", 3, "compute"), files)

    def test_node_trace(self) -> None:
        parsed = trace_mod.parse_trace(NODE_TRACE)
        self.assertEqual(parsed.language, "node")
        self.assertEqual(parsed.error_type, "TypeError")
        locs = [(f.file, f.line) for f in parsed.frames]
        self.assertIn(("src/user.js", 42), locs)
        self.assertIn(("src/index.js", 7), locs)

    def test_generic_trace_extracts_path_line(self) -> None:
        parsed = trace_mod.parse_trace("Something failed at src/foo.py:99 unexpectedly")
        locs = [(f.file, f.line) for f in parsed.frames]
        self.assertIn(("src/foo.py", 99), locs)

    def test_plain_message_no_frames(self) -> None:
        parsed = trace_mod.parse_trace("connection refused")
        self.assertEqual(parsed.frames, [])
        self.assertIn("connection refused", parsed.error_message or "")


class DebugDataTestCase(unittest.TestCase):
    """Isolated home + an indexed sample project for location/diagnosis tests."""

    def setUp(self) -> None:
        self._prev = os.environ.get("DEVOS_HOME")
        self._home = tempfile.TemporaryDirectory()
        os.environ["DEVOS_HOME"] = self._home.name
        self.ws = Workspace.load()
        self.ws.initialize().close()
        self._proj = tempfile.TemporaryDirectory()
        self.root = Path(self._proj.name)
        _write(self.root, "src/calc.py",
               "def compute(divisor):\n    # divide a constant by the divisor\n    return 1 / divisor\n")
        _write(self.root, "src/app.py",
               "from src.calc import compute\n\ndef handler(value):\n    return compute(value)\n")
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


class TestFindFileByPath(DebugDataTestCase):
    def test_exact_rel_path(self) -> None:
        conn = self.ws.connect()
        try:
            row = repo.find_file_by_path(conn, self.pid, "src/calc.py")
            self.assertIsNotNone(row)
            self.assertEqual(row["rel_path"], "src/calc.py")
        finally:
            conn.close()

    def test_basename_suffix_match(self) -> None:
        conn = self.ws.connect()
        try:
            row = repo.find_file_by_path(conn, self.pid, "calc.py")
            self.assertIsNotNone(row)
            self.assertEqual(row["rel_path"], "src/calc.py")
        finally:
            conn.close()

    def test_backslash_path_normalized(self) -> None:
        conn = self.ws.connect()
        try:
            row = repo.find_file_by_path(conn, self.pid, "src\\calc.py")
            self.assertEqual(row["rel_path"], "src/calc.py")
        finally:
            conn.close()

    def test_unknown_returns_none(self) -> None:
        conn = self.ws.connect()
        try:
            self.assertIsNone(repo.find_file_by_path(conn, self.pid, "does/not/exist.py"))
        finally:
            conn.close()


class TestResolveProjectPublic(DebugDataTestCase):
    def test_resolve_single_project(self) -> None:
        from devos.modules import qa
        conn = self.ws.connect()
        try:
            self.assertEqual(qa.resolve_project(conn, None), (self.pid, "demo"))
            self.assertEqual(qa.resolve_project(conn, "demo"), (self.pid, "demo"))
        finally:
            conn.close()


class TestDiagnose(DebugDataTestCase):
    def test_locates_frame_in_index_and_grounds(self) -> None:
        conn = self.ws.connect()
        try:
            diag = debug_mod.diagnose(conn, PY_TRACE, provider=MockAIProvider())
            self.assertTrue(diag.grounded)
            self.assertEqual(diag.error_type, "ZeroDivisionError")
            located = {lf.rel_path for lf in diag.located_frames}
            self.assertIn("src/calc.py", located)
            self.assertIn("src/app.py", located)
            self.assertEqual(diag.confidence, "high")
            calc = next(lf for lf in diag.located_frames if lf.rel_path == "src/calc.py")
            self.assertIsNotNone(calc.chunk)
            self.assertIn("divisor", calc.chunk.content)
        finally:
            conn.close()

    def test_sources_include_located_files(self) -> None:
        conn = self.ws.connect()
        try:
            diag = debug_mod.diagnose(conn, PY_TRACE, provider=MockAIProvider())
            src_paths = {s.rel_path for s in diag.sources}
            self.assertIn("src/calc.py", src_paths)
        finally:
            conn.close()

    def test_unlocatable_trace_declines_without_provider(self) -> None:
        class BoomProvider(MockAIProvider):
            def complete(self, *a, **k):
                raise AssertionError("provider must not be called without evidence")
        conn = self.ws.connect()
        try:
            trace = ('Traceback (most recent call last):\n'
                     '  File "/external/lib/zzzqqq.py", line 5, in nope\n'
                     'KeyError: \'zzqqxx_absent_symbol\'')
            diag = debug_mod.diagnose(conn, trace, provider=BoomProvider())
            self.assertFalse(diag.grounded)
            self.assertEqual(diag.confidence, "low")
            self.assertEqual(diag.sources, [])
        finally:
            conn.close()

    def test_does_not_read_filesystem_paths_from_trace(self) -> None:
        # A trace naming a real on-disk file OUTSIDE the project must not be located/read.
        conn = self.ws.connect()
        try:
            outside = Path(self._home.name) / "secret.txt"
            outside.write_text("TOP SECRET", encoding="utf-8")
            trace = f'Traceback (most recent call last):\n  File "{outside}", line 1, in x\nError: boom'
            diag = debug_mod.diagnose(conn, trace, provider=MockAIProvider())
            self.assertTrue(all("TOP SECRET" not in (s.content or "") for s in diag.sources))
        finally:
            conn.close()

    def test_build_debug_query_uses_message_and_funcs(self) -> None:
        parsed = trace_mod.parse_trace(PY_TRACE)
        q = debug_mod.build_debug_query(parsed)
        self.assertIn("compute", q)


class TestDebugCli(DebugDataTestCase):
    def _run(self, *argv):
        buf = io.StringIO()
        prev_stdin = sys.stdin
        sys.stdin = io.StringIO("")  # deterministic empty, non-tty stdin (no blocking read)
        try:
            with redirect_stdout(buf):
                code = main(list(argv))
        finally:
            sys.stdin = prev_stdin
        return code, buf.getvalue()

    def test_debug_from_file_reports_evidence_and_sources(self) -> None:
        tracefile = Path(self._home.name) / "trace.txt"
        tracefile.write_text(PY_TRACE, encoding="utf-8")
        code, out = self._run("debug", "--file", str(tracefile))
        self.assertEqual(code, 0)
        self.assertIn("Observed evidence", out)
        self.assertIn("src/calc.py", out)
        self.assertIn("Sources", out)
        self.assertIn("Confidence", out)

    def test_debug_inline_text(self) -> None:
        code, out = self._run("debug", "ZeroDivisionError: division by zero at src/calc.py:3")
        self.assertEqual(code, 0)
        self.assertIn("src/calc.py", out)

    def test_debug_no_input_errors(self) -> None:
        code, out = self._run("debug")
        self.assertEqual(code, 1)
        self.assertIn("provide", out.lower())
