"""Phase 9 (slice 6) — Meeting/Transcript foundation tests (TDD, stdlib unittest)."""
from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from devos.cli import main
from devos.core.workspace import Workspace
from devos.modules import meeting as meeting_mod
from devos.providers.ai import MockAIProvider


class TestSummarize(unittest.TestCase):
    def test_grounded_summary(self) -> None:
        text = ("Standup notes: Alice will fix the login bug. "
                "Decision: ship on Friday. Bob to update the docs.")
        s = meeting_mod.summarize(text, provider=MockAIProvider(), source_label="notes.txt")
        self.assertTrue(s.grounded)
        self.assertEqual(s.source_label, "notes.txt")
        self.assertEqual(s.provider, "mock")
        self.assertIn("login bug", s.text)  # mock echoes the grounded transcript

    def test_empty_declines_without_provider(self) -> None:
        class BoomProvider(MockAIProvider):
            def complete(self, *a, **k):
                raise AssertionError("provider must not be called on empty transcript")
        s = meeting_mod.summarize("   \n  ", provider=BoomProvider())
        self.assertFalse(s.grounded)
        self.assertIn("empty", s.text.lower())

    def test_long_transcript_is_truncated(self) -> None:
        big = "word " * (meeting_mod.MAX_TRANSCRIPT_CHARS)  # well over the cap

        captured = {}

        class CapProvider(MockAIProvider):
            def complete(self, prompt, *, system=None, context=None):
                captured["context_len"] = len(context or "")
                return super().complete(prompt, system=system, context=context)

        meeting_mod.summarize(big, provider=CapProvider(), source_label="big.txt")
        self.assertLessEqual(captured["context_len"], meeting_mod.MAX_TRANSCRIPT_CHARS + 200)


class MeetingCliTestCase(unittest.TestCase):
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

    def _run(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_summarize_file(self) -> None:
        f = Path(self._home.name) / "notes.txt"
        f.write_text("Decision: ship Friday. Alice to fix login bug.", encoding="utf-8")
        code, out = self._run("meeting", "summarize", str(f))
        self.assertEqual(code, 0)
        self.assertIn("Source", out)
        self.assertIn("login bug", out)

    def test_missing_file_errors(self) -> None:
        code, out = self._run("meeting", "summarize", str(Path(self._home.name) / "nope.txt"))
        self.assertEqual(code, 1)
        self.assertIn("cannot read", out.lower())

    def test_empty_file_declines(self) -> None:
        f = Path(self._home.name) / "empty.txt"
        f.write_text("   ", encoding="utf-8")
        code, out = self._run("meeting", "summarize", str(f))
        self.assertEqual(code, 0)
        self.assertIn("empty", out.lower())
