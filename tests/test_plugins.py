"""Phase 9 (slice 5) — Plugin/extension seam tests (TDD, stdlib unittest)."""
from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from devos import plugins as plugins_mod
from devos.cli import main
from devos.commands import base as cmd_base
from devos.providers import ai as ai_mod


class TestRegisterProvider(unittest.TestCase):
    def setUp(self) -> None:
        self._snapshot = dict(ai_mod._REGISTRY)

    def tearDown(self) -> None:
        ai_mod._REGISTRY.clear()
        ai_mod._REGISTRY.update(self._snapshot)

    def test_register_and_get(self) -> None:
        class EchoProvider(ai_mod.MockAIProvider):
            name = "echo"

        ai_mod.register_provider("echo", EchoProvider)
        self.assertIn("echo", ai_mod.available_providers())
        self.assertIsInstance(ai_mod.get_provider("echo"), EchoProvider)
