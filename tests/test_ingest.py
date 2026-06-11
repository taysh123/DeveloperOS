"""Phase 2 — project ingestion tests (TDD, stdlib unittest).

Covers the pure classification/ignore helpers, idempotent scanning into SQLite, and
the `devos scan` / `devos projects` CLI commands. All filesystem and DB state is
isolated in temp dirs (DEVOS_HOME override), so the suite never touches a real install.
"""
from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from devos.cli import main
from devos.core.workspace import Workspace
from devos.modules import ingest
from devos.storage import repo


def _write(root: Path, rel: str, content: str = "x") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


class TestClassify(unittest.TestCase):
    def test_frontend_by_extension(self) -> None:
        self.assertEqual(ingest.classify("src/components/Button.tsx")[1], "frontend")
        self.assertEqual(ingest.classify("styles/app.css")[1], "frontend")

    def test_backend_by_extension(self) -> None:
        self.assertEqual(ingest.classify("server/app.py")[1], "backend")
        self.assertEqual(ingest.classify("cmd/main.go")[1], "backend")

    def test_test_files(self) -> None:
        self.assertEqual(ingest.classify("tests/test_app.py")[1], "test")
        self.assertEqual(ingest.classify("src/Button.test.tsx")[1], "test")

    def test_config_files(self) -> None:
        self.assertEqual(ingest.classify("package.json")[1], "config")
        self.assertEqual(ingest.classify("pyproject.toml")[1], "config")
        self.assertEqual(ingest.classify("Dockerfile")[1], "config")

    def test_db_files(self) -> None:
        self.assertEqual(ingest.classify("db/migrations/001_init.sql")[1], "db")
        self.assertEqual(ingest.classify("prisma/schema.prisma")[1], "db")

    def test_auth_files(self) -> None:
        self.assertEqual(ingest.classify("src/auth/login.py")[1], "auth")

    def test_api_files(self) -> None:
        self.assertEqual(ingest.classify("api/routes.py")[1], "api")

    def test_other_fallback(self) -> None:
        self.assertEqual(ingest.classify("README.md")[1], "other")

    def test_language_detection(self) -> None:
        self.assertEqual(ingest.classify("server/app.py")[0], "python")
        self.assertEqual(ingest.classify("src/x.tsx")[0], "tsx")


class TestBinaryDetection(unittest.TestCase):
    def test_text_is_not_binary(self) -> None:
        self.assertFalse(ingest.is_binary_bytes(b"hello world\n"))

    def test_nulls_are_binary(self) -> None:
        self.assertTrue(ingest.is_binary_bytes(b"\x00\x01\x02binary"))


class IngestTestCase(unittest.TestCase):
    """Sets up an isolated DeveloperOS home + initialized DB and a sample project tree."""

    def setUp(self) -> None:
        self._prev = os.environ.get("DEVOS_HOME")
        self._home = tempfile.TemporaryDirectory()
        os.environ["DEVOS_HOME"] = self._home.name
        self.ws = Workspace.load()
        self.ws.initialize().close()

        self._proj = tempfile.TemporaryDirectory()
        self.root = Path(self._proj.name)
        # A representative project tree.
        _write(self.root, "src/components/Button.tsx", "export const Button = () => null;")
        _write(self.root, "server/app.py", "print('hi')")
        _write(self.root, "tests/test_app.py", "def test_x():\n    assert True")
        _write(self.root, "package.json", '{"name":"demo"}')
        _write(self.root, "db/migrations/001_init.sql", "CREATE TABLE t(id INT);")
        # Should be ignored:
        _write(self.root, "node_modules/dep/index.js", "module.exports = {}")
        _write(self.root, ".git/config", "[core]")

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("DEVOS_HOME", None)
        else:
            os.environ["DEVOS_HOME"] = self._prev
        self._home.cleanup()
        self._proj.cleanup()


class TestScan(IngestTestCase):
    def test_scan_records_inventory_and_applies_ignores(self) -> None:
        conn = self.ws.connect()
        try:
            result = ingest.scan_project(conn, self.root)
            # 5 real files; node_modules and .git excluded.
            self.assertEqual(result.total, 5)
            self.assertEqual(result.added, 5)
            self.assertEqual(result.updated, 0)
            self.assertEqual(result.by_category.get("frontend"), 1)
            self.assertEqual(result.by_category.get("backend"), 1)
            self.assertEqual(result.by_category.get("test"), 1)
            self.assertEqual(result.by_category.get("config"), 1)
            self.assertEqual(result.by_category.get("db"), 1)

            paths = set(repo.file_paths(conn, result.project_id))
            self.assertIn("src/components/Button.tsx", paths)
            self.assertNotIn("node_modules/dep/index.js", paths)
            self.assertFalse(any(p.startswith(".git/") for p in paths))
        finally:
            conn.close()

    def test_rescan_is_idempotent(self) -> None:
        conn = self.ws.connect()
        try:
            first = ingest.scan_project(conn, self.root)
            second = ingest.scan_project(conn, self.root)
            self.assertEqual(second.added, 0)
            self.assertEqual(second.updated, 0)
            self.assertEqual(second.unchanged, first.total)
            self.assertEqual(second.total, first.total)
            # Re-scanning the same path must not create a duplicate project.
            self.assertEqual(len(repo.list_projects(conn)), 1)
            self.assertEqual(second.project_id, first.project_id)
        finally:
            conn.close()

    def test_rescan_detects_add_modify_delete(self) -> None:
        conn = self.ws.connect()
        try:
            ingest.scan_project(conn, self.root)

            # modify one, add one, delete one
            _write(self.root, "server/app.py", "print('changed')")
            _write(self.root, "src/new_feature.ts", "export const x = 1;")
            (self.root / "package.json").unlink()

            result = ingest.scan_project(conn, self.root)
            self.assertEqual(result.added, 1)
            self.assertEqual(result.updated, 1)
            self.assertEqual(result.removed, 1)
            self.assertEqual(result.total, 5)  # 5 - 1 deleted + 1 added
        finally:
            conn.close()


class TestScanCli(IngestTestCase):
    def _run(self, *argv: str) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_scan_then_projects(self) -> None:
        code, out = self._run("scan", str(self.root))
        self.assertEqual(code, 0)
        self.assertIn("5", out)  # reports 5 files

        code, out = self._run("projects")
        self.assertEqual(code, 0)
        self.assertIn(self.root.name, out)


if __name__ == "__main__":
    unittest.main()


class TestSecretAwareScan(unittest.TestCase):
    """Secret-aware indexing: credential-looking files never reach the DB or index."""

    def setUp(self) -> None:
        self._prev = os.environ.get("DEVOS_HOME")
        self._home = tempfile.TemporaryDirectory()
        os.environ["DEVOS_HOME"] = self._home.name
        ws = Workspace.load()
        ws.initialize().close()
        self.conn = ws.connect()
        self._proj = tempfile.TemporaryDirectory()
        self.root = Path(self._proj.name)

    def tearDown(self) -> None:
        self.conn.close()
        if self._prev is None:
            os.environ.pop("DEVOS_HOME", None)
        else:
            os.environ["DEVOS_HOME"] = self._prev
        self._home.cleanup()
        self._proj.cleanup()

    def test_pattern_matcher(self) -> None:
        for name in (".env", ".env.local", "server.pem", "deploy.key", "id_rsa",
                     "id_rsa.pub", ".npmrc", "credentials.json", "API.SECRET",
                     "service-account-prod.json", "secrets.yaml"):
            self.assertTrue(ingest.is_secret_file(name), name)
        for name in ("app.py", "environment.md", "keyboard.js", "monkey.txt",
                     "requirements.txt", "envoy.yaml"):
            self.assertFalse(ingest.is_secret_file(name), name)

    def test_secret_files_are_skipped_and_counted(self) -> None:
        (self.root / "app.py").write_text("print('ok')\n", encoding="utf-8")
        (self.root / ".env").write_text("AWS_SECRET=hunter2\n", encoding="utf-8")
        (self.root / "deploy.pem").write_text("-----BEGIN PRIVATE KEY-----\n", encoding="utf-8")
        result = ingest.scan_project(self.conn, self.root, name="secrets-demo")
        self.assertEqual(result.skipped_secrets, 2)
        self.assertGreaterEqual(result.skipped, 2)
        rows = self.conn.execute(
            "SELECT rel_path FROM files WHERE project_id = ?", (result.project_id,)
        ).fetchall()
        paths = {r["rel_path"] for r in rows}
        self.assertEqual(paths, {"app.py"})

    def test_secret_content_never_reaches_the_index(self) -> None:
        (self.root / "app.py").write_text("print('ok')\n", encoding="utf-8")
        (self.root / ".env").write_text("TOP_SECRET_TOKEN=zzqqsecretzz\n", encoding="utf-8")
        from devos.modules import index as index_mod
        result = ingest.scan_project(self.conn, self.root, name="secrets-idx")
        index_mod.index_project(self.conn, result.project_id)
        hit = self.conn.execute(
            "SELECT COUNT(*) AS c FROM chunks_fts WHERE content LIKE '%zzqqsecretzz%'"
        ).fetchone()
        self.assertEqual(hit["c"], 0)
