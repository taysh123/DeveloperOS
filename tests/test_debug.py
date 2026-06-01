"""Phase 5 — Debug Assistant tests (TDD, stdlib unittest)."""
from __future__ import annotations

import io
import os
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
