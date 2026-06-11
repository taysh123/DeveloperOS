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

    def test_bom_file_no_stray_char(self) -> None:
        # Files saved as "UTF-8 with BOM" (common on Windows) must not leak ﻿ into output.
        f = Path(self._home.name) / "bom.txt"
        f.write_bytes(b"\xef\xbb\xbfDecision: ship Friday.")
        code, out = self._run("meeting", "summarize", str(f))
        self.assertEqual(code, 0)
        self.assertNotIn("﻿", out)
        self.assertIn("ship Friday", out)

    def test_empty_file_declines(self) -> None:
        f = Path(self._home.name) / "empty.txt"
        f.write_text("   ", encoding="utf-8")
        code, out = self._run("meeting", "summarize", str(f))
        self.assertEqual(code, 0)
        self.assertIn("empty", out.lower())


class TestExtractActionItems(unittest.TestCase):
    """Slice 9 — deterministic action-item extraction for the dashboard bridge."""

    def test_keyword_prefixed_lines(self) -> None:
        text = ("We talked about the release.\n"
                "TODO: fix the login bug\n"
                "Action: Bob updates the docs\n"
                "Next step: tag v0.6.0\n")
        items = meeting_mod.extract_action_items(text)
        self.assertEqual(items, ["fix the login bug", "Bob updates the docs", "tag v0.6.0"])

    def test_bullets_only_count_inside_action_sections(self) -> None:
        text = ("Summary\n- this bullet is narrative, not an action\n\n"
                "Action items\n- ship the meeting tab\n* write tests\n"
                "- [ ] update the changelog\n")
        items = meeting_mod.extract_action_items(text)
        self.assertEqual(items, ["ship the meeting tab", "write tests", "update the changelog"])

    def test_dedupes_caps_and_handles_empty(self) -> None:
        self.assertEqual(meeting_mod.extract_action_items(""), [])
        self.assertEqual(meeting_mod.extract_action_items("   \n  "), [])
        text = "Next steps\n" + "\n".join(f"- item {i}" for i in range(30))
        self.assertEqual(len(meeting_mod.extract_action_items(text)),
                         meeting_mod.MAX_ACTION_ITEMS)
        dup = "TODO: same thing\ntodo: Same Thing\n"
        self.assertEqual(meeting_mod.extract_action_items(dup), ["same thing"])

    def test_never_calls_a_provider(self) -> None:
        # Pure function of the text — nothing to patch, but assert no provider arg exists.
        import inspect
        params = inspect.signature(meeting_mod.extract_action_items).parameters
        self.assertNotIn("provider", params)
