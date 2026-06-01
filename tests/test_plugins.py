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


class PluginIsolationMixin:
    """Snapshot/restore global registries + plugin state so tests don't leak."""

    def _snap(self) -> None:
        self._cmds = list(cmd_base.COMMANDS)
        self._prov = dict(ai_mod._REGISTRY)
        self._loaded = list(plugins_mod.LOADED)
        self._errors = list(plugins_mod.ERRORS)

    def _restore(self) -> None:
        cmd_base.COMMANDS[:] = self._cmds
        ai_mod._REGISTRY.clear(); ai_mod._REGISTRY.update(self._prov)
        plugins_mod.LOADED[:] = self._loaded
        plugins_mod.ERRORS[:] = self._errors


def _fake_ep(name, fn):
    class _EP:
        def __init__(self, n, f):
            self.name = n
            self._f = f
        def load(self):
            return self._f
    return _EP(name, fn)


class TestPluginLoading(PluginIsolationMixin, unittest.TestCase):
    def setUp(self) -> None:
        self._snap()
        plugins_mod.LOADED.clear()
        plugins_mod.ERRORS.clear()

    def tearDown(self) -> None:
        self._restore()

    def test_entry_point_plugin_registers_command(self) -> None:
        def register_ping():
            @cmd_base.register
            class PingCommand(cmd_base.Command):
                name = "pluginping"
                help = "ping from a plugin"
                def run(self, args, ws):
                    print("pong")
                    return 0

        loaded = plugins_mod.load_entry_point_plugins(eps=[_fake_ep("pingpkg", register_ping)])
        self.assertIn("pingpkg", loaded)
        self.assertTrue(any(c.name == "pluginping" for c in cmd_base.COMMANDS))

    def test_broken_plugin_is_isolated(self) -> None:
        def boom():
            raise RuntimeError("plugin exploded")

        loaded = plugins_mod.load_entry_point_plugins(eps=[_fake_ep("badpkg", boom)])
        self.assertEqual(loaded, [])
        self.assertTrue(any(name == "badpkg" for name, _ in plugins_mod.ERRORS))

    def test_local_plugin_dir_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "hello_plugin.py").write_text(
                "from devos.commands.base import Command, register\n"
                "@register\n"
                "class HelloPlugin(Command):\n"
                "    name = 'plughello'\n"
                "    help = 'hi'\n"
                "    def run(self, args, ws):\n"
                "        print('hi from plugin')\n"
                "        return 0\n",
                encoding="utf-8",
            )
            loaded = plugins_mod.load_local_plugins(Path(tmp))
            self.assertIn("hello_plugin", loaded)
            self.assertTrue(any(c.name == "plughello" for c in cmd_base.COMMANDS))

    def test_load_local_missing_dir_is_noop(self) -> None:
        self.assertEqual(plugins_mod.load_local_plugins(Path("/no/such/dir/xyz")), [])
