"""Phase 8 — Documentation Automation tests (TDD, stdlib unittest)."""
from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from devos.cli import main
from devos.core.workspace import Workspace
from devos.modules import docgen as docgen_mod
from devos.modules import index as index_mod
from devos.modules import ingest
from devos.providers.ai import MockAIProvider
from devos.storage import repo


def _write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


class DocgenTestCase(unittest.TestCase):
    """Isolated home + an indexed sample project."""

    def setUp(self) -> None:
        self._prev = os.environ.get("DEVOS_HOME")
        self._home = tempfile.TemporaryDirectory()
        os.environ["DEVOS_HOME"] = self._home.name
        self.ws = Workspace.load()
        self.ws.initialize().close()
        self._proj = tempfile.TemporaryDirectory()
        self.root = Path(self._proj.name)
        _write(self.root, "src/app.py",
               "def main():\n    # entrypoint for the demo service\n    return run_server()\n")
        _write(self.root, "README.md", "# Demo\nA small service.\n")
        _write(self.root, "pyproject.toml", "[project]\nname='demo'\n")
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


class TestCodeDocs(DocgenTestCase):
    def test_readme_is_grounded_with_sources(self) -> None:
        conn = self.ws.connect()
        try:
            doc = docgen_mod.generate(conn, "readme", provider=MockAIProvider(), project="demo")
        finally:
            conn.close()
        self.assertEqual(doc.doc_type, "readme")
        self.assertTrue(doc.grounded)
        self.assertTrue(doc.sources)
        self.assertEqual(doc.provider, "mock")
        # mock echoes the assembled context (which includes project facts)
        self.assertIn("demo", doc.text)

    def test_architecture_and_api_and_setup_types(self) -> None:
        conn = self.ws.connect()
        try:
            for t in ("architecture", "api", "setup"):
                doc = docgen_mod.generate(conn, t, provider=MockAIProvider(), project="demo")
                self.assertEqual(doc.doc_type, t)
                self.assertTrue(doc.grounded, t)
        finally:
            conn.close()

    def test_unknown_type_raises(self) -> None:
        conn = self.ws.connect()
        try:
            with self.assertRaises(ValueError):
                docgen_mod.generate(conn, "nope", provider=MockAIProvider(), project="demo")
        finally:
            conn.close()

    def test_declines_when_nothing_indexed(self) -> None:
        # a second, empty project (registered but no files/chunks)
        empty = tempfile.TemporaryDirectory()
        self.addCleanup(empty.cleanup)
        conn = self.ws.connect()
        try:
            epid = repo.upsert_project(conn, empty.name, "empty")
            conn.commit()

            class BoomProvider(MockAIProvider):
                def complete(self, *a, **k):
                    raise AssertionError("provider must not be called without grounding")

            doc = docgen_mod.generate(conn, "readme", provider=BoomProvider(), project="empty")
            self.assertFalse(doc.grounded)
            self.assertEqual(doc.sources, [])
        finally:
            conn.close()
