"""Phase 9 (slice 1) — Learning Assistant tests (TDD, stdlib unittest)."""
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
from devos.modules import learning as learning_mod
from devos.providers.ai import MockAIProvider


def _write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


class LearnTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._prev = os.environ.get("DEVOS_HOME")
        self._home = tempfile.TemporaryDirectory()
        os.environ["DEVOS_HOME"] = self._home.name
        self.ws = Workspace.load()
        self.ws.initialize().close()
        self._proj = tempfile.TemporaryDirectory()
        self.root = Path(self._proj.name)
        _write(self.root, "src/retrieval.py",
               "def retrieve(query):\n    # search the index and rank results\n    return ranked(query)\n")
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


class TestLearn(LearnTestCase):
    def test_file_mode_grounds_on_that_file(self) -> None:
        conn = self.ws.connect()
        try:
            lesson = learning_mod.learn(conn, "src/retrieval.py",
                                        provider=MockAIProvider(), level="eli5", project="demo")
            self.assertTrue(lesson.grounded)
            self.assertEqual(lesson.level, "eli5")
            self.assertTrue(any(s.rel_path == "src/retrieval.py" for s in lesson.sources))
            self.assertIn("retrieve", lesson.text)  # mock echoes grounded context
        finally:
            conn.close()

    def test_topic_mode_retrieves(self) -> None:
        conn = self.ws.connect()
        try:
            lesson = learning_mod.learn(conn, "ranked search index",
                                        provider=MockAIProvider(), level="advanced", project="demo")
            self.assertTrue(lesson.grounded)
            self.assertTrue(lesson.sources)
        finally:
            conn.close()

    def test_invalid_level_raises(self) -> None:
        conn = self.ws.connect()
        try:
            with self.assertRaises(ValueError):
                learning_mod.learn(conn, "src/retrieval.py",
                                   provider=MockAIProvider(), level="genius", project="demo")
        finally:
            conn.close()

    def test_declines_without_grounding(self) -> None:
        class BoomProvider(MockAIProvider):
            def complete(self, *a, **k):
                raise AssertionError("provider must not be called without grounding")
        conn = self.ws.connect()
        try:
            lesson = learning_mod.learn(conn, "zzz_absent_topic_qqq",
                                        provider=BoomProvider(), project="demo")
            self.assertFalse(lesson.grounded)
            self.assertEqual(lesson.sources, [])
        finally:
            conn.close()
