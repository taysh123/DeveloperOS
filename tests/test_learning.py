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


class TestQuiz(LearnTestCase):
    def test_file_mode_questions_grounded(self) -> None:
        conn = self.ws.connect()
        try:
            quiz = learning_mod.quiz(conn, "src/retrieval.py",
                                     provider=MockAIProvider(), n=3, project="demo")
            self.assertTrue(quiz.grounded)
            self.assertEqual(quiz.n, 3)
            self.assertTrue(any(s.rel_path == "src/retrieval.py" for s in quiz.sources))
            self.assertIn("retrieve", quiz.text)  # mock echoes grounded context
        finally:
            conn.close()

    def test_topic_mode(self) -> None:
        conn = self.ws.connect()
        try:
            quiz = learning_mod.quiz(conn, "ranked search index",
                                     provider=MockAIProvider(), project="demo")
            self.assertTrue(quiz.grounded)
            self.assertTrue(quiz.sources)
        finally:
            conn.close()

    def test_invalid_n_raises(self) -> None:
        conn = self.ws.connect()
        try:
            with self.assertRaises(ValueError):
                learning_mod.quiz(conn, "src/retrieval.py",
                                  provider=MockAIProvider(), n=0, project="demo")
        finally:
            conn.close()

    def test_n_clamped_to_max(self) -> None:
        conn = self.ws.connect()
        try:
            quiz = learning_mod.quiz(conn, "src/retrieval.py",
                                     provider=MockAIProvider(), n=999, project="demo")
            self.assertLessEqual(quiz.n, 20)
        finally:
            conn.close()

    def test_declines_without_grounding(self) -> None:
        class BoomProvider(MockAIProvider):
            def complete(self, *a, **k):
                raise AssertionError("provider must not be called without grounding")
        conn = self.ws.connect()
        try:
            quiz = learning_mod.quiz(conn, "zzz_absent_topic_qqq",
                                     provider=BoomProvider(), project="demo")
            self.assertFalse(quiz.grounded)
            self.assertEqual(quiz.sources, [])
        finally:
            conn.close()


class TestExercise(LearnTestCase):
    def test_file_mode_grounded(self) -> None:
        conn = self.ws.connect()
        try:
            ex = learning_mod.exercise(conn, "src/retrieval.py",
                                       provider=MockAIProvider(), n=2, project="demo")
            self.assertTrue(ex.grounded)
            self.assertEqual(ex.n, 2)
            self.assertTrue(any(s.rel_path == "src/retrieval.py" for s in ex.sources))
        finally:
            conn.close()

    def test_topic_mode(self) -> None:
        conn = self.ws.connect()
        try:
            ex = learning_mod.exercise(conn, "ranked search index",
                                       provider=MockAIProvider(), project="demo")
            self.assertTrue(ex.grounded)
            self.assertTrue(ex.sources)
        finally:
            conn.close()

    def test_invalid_n_raises(self) -> None:
        conn = self.ws.connect()
        try:
            with self.assertRaises(ValueError):
                learning_mod.exercise(conn, "src/retrieval.py",
                                      provider=MockAIProvider(), n=0, project="demo")
        finally:
            conn.close()

    def test_declines_without_grounding(self) -> None:
        class BoomProvider(MockAIProvider):
            def complete(self, *a, **k):
                raise AssertionError("provider must not be called without grounding")
        conn = self.ws.connect()
        try:
            ex = learning_mod.exercise(conn, "zzz_absent_topic_qqq",
                                       provider=BoomProvider(), project="demo")
            self.assertFalse(ex.grounded)
            self.assertEqual(ex.sources, [])
        finally:
            conn.close()


class TestLearnCli(LearnTestCase):
    def _run(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_learn_file_prints_text_and_sources(self) -> None:
        code, out = self._run("learn", "src/retrieval.py", "--level", "eli5", "--project", "demo")
        self.assertEqual(code, 0)
        self.assertIn("Sources", out)
        self.assertIn("src/retrieval.py", out)

    def test_learn_topic_mode(self) -> None:
        code, out = self._run("learn", "ranked", "search", "index", "--project", "demo")
        self.assertEqual(code, 0)
        self.assertIn("Sources", out)

    def test_learn_declines(self) -> None:
        code, out = self._run("learn", "zzz_absent_topic_qqq", "--project", "demo")
        self.assertEqual(code, 0)
        self.assertIn("don't have enough", out)


class TestQuizCli(LearnTestCase):
    def _run(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_quiz_file_prints_text_and_sources(self) -> None:
        code, out = self._run("quiz", "src/retrieval.py", "--n", "3", "--project", "demo")
        self.assertEqual(code, 0)
        self.assertIn("Sources", out)
        self.assertIn("src/retrieval.py", out)

    def test_quiz_declines(self) -> None:
        code, out = self._run("quiz", "zzz_absent_topic_qqq", "--project", "demo")
        self.assertEqual(code, 0)
        self.assertIn("don't have enough", out)
