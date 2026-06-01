"""Foundation smoke tests (stdlib unittest; also pytest-discoverable).

Each test isolates the data dir via the DEVOS_HOME env var + a temp directory, so the
suite never touches a real machine-level DeveloperOS install.
"""
from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from devos import __version__
from devos.cli import main
from devos.config import load_config
from devos.providers.ai import MockAIProvider, get_provider
from devos.storage import db


class TempHomeTestCase(unittest.TestCase):
    """Base case that points DEVOS_HOME at an isolated temp directory."""

    def setUp(self) -> None:
        self._prev = os.environ.get("DEVOS_HOME")
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["DEVOS_HOME"] = self._tmp.name

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("DEVOS_HOME", None)
        else:
            os.environ["DEVOS_HOME"] = self._prev
        self._tmp.cleanup()


class TestVersion(unittest.TestCase):
    def test_version_string(self) -> None:
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+$")


class TestConfig(TempHomeTestCase):
    def test_data_dir_follows_env_override(self) -> None:
        cfg = load_config()
        self.assertEqual(cfg.data_dir, Path(self._tmp.name))
        self.assertFalse(cfg.is_initialized())


class TestStorage(TempHomeTestCase):
    def test_initialize_is_idempotent_and_creates_tables(self) -> None:
        cfg = load_config()
        conn = db.initialize(cfg.db_path)
        try:
            self.assertEqual(db.schema_version(conn), db.SCHEMA_VERSION)
            counts = db.table_counts(conn)
            self.assertEqual(set(counts), set(db.COUNTED_TABLES))
            self.assertTrue(all(v == 0 for v in counts.values()))
        finally:
            conn.close()

        # Re-running must not error and must keep the same version.
        conn2 = db.initialize(cfg.db_path)
        try:
            self.assertEqual(db.schema_version(conn2), db.SCHEMA_VERSION)
        finally:
            conn2.close()

    def test_fts5_table_exists(self) -> None:
        cfg = load_config()
        conn = db.initialize(cfg.db_path)
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE name = 'chunks_fts';"
            ).fetchone()
            self.assertIsNotNone(row)
        finally:
            conn.close()


class TestProvider(unittest.TestCase):
    def test_mock_provider_is_default(self) -> None:
        provider = get_provider()
        self.assertIsInstance(provider, MockAIProvider)

    def test_mock_completion_echoes_prompt(self) -> None:
        result = get_provider("mock").complete("hello", context="ctx")
        self.assertEqual(result.provider, "mock")
        self.assertIn("hello", result.text)
        self.assertTrue(result.meta.get("mock"))

    def test_unknown_provider_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_provider("does-not-exist")


class TestCli(TempHomeTestCase):
    def _run(self, *argv: str) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_status_before_init(self) -> None:
        code, out = self._run("status")
        self.assertEqual(code, 0)
        self.assertIn("NOT initialized", out)

    def test_init_then_status(self) -> None:
        code, out = self._run("init")
        self.assertEqual(code, 0)
        self.assertIn("initialized", out)

        code, out = self._run("status")
        self.assertEqual(code, 0)
        self.assertIn("schema", out)
        self.assertIn("projects", out)

    def test_no_command_prints_help(self) -> None:
        code, out = self._run()
        self.assertEqual(code, 0)
        self.assertIn("usage", out.lower())


if __name__ == "__main__":
    unittest.main()
