"""Desktop ladder step B — `devos app` launcher tests (TDD, stdlib unittest).

Lifecycle under test (D-0030): probe -> reuse-or-start -> ready-wait -> open ->
serve (blocking). Single instance is guaranteed per port by a read-only probe of
GET /api/session; a non-DeveloperOS occupant must produce a friendly error.
"""
from __future__ import annotations

import http.server
import io
import os
import socket
import tempfile
import threading
import unittest
from contextlib import redirect_stdout

from devos.cli import main
from devos.core.workspace import Workspace


class _IsolatedHome(unittest.TestCase):
    def setUp(self) -> None:
        self._prev = os.environ.get("DEVOS_HOME")
        self._home = tempfile.TemporaryDirectory()
        os.environ["DEVOS_HOME"] = self._home.name

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("DEVOS_HOME", None)
        else:
            os.environ["DEVOS_HOME"] = self._prev
        self._home.cleanup()


def _start_devos_server(case: unittest.TestCase) -> int:
    """A real DeveloperOS dashboard server on an ephemeral port (initialized home)."""
    Workspace.load().initialize().close()
    from devos.api import server as api_server
    srv = api_server.create_server("127.0.0.1", 0)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    case.addCleanup(th.join, 5)
    case.addCleanup(srv.server_close)
    case.addCleanup(srv.shutdown)
    return port


def _start_other_server(case: unittest.TestCase) -> int:
    """A non-DeveloperOS HTTP server (404s everything) on an ephemeral port."""

    class Quiet(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (stdlib casing)
            self.send_error(404)

        def log_message(self, *a):  # silence test output
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    case.addCleanup(th.join, 5)
    case.addCleanup(srv.server_close)
    case.addCleanup(srv.shutdown)
    return port


def _free_port() -> int:
    """A port that nothing listens on (bind ephemeral, release)."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestRegistration(unittest.TestCase):
    def test_app_is_registered(self) -> None:
        from devos.commands import COMMANDS
        self.assertIn("app", {cls.name for cls in COMMANDS})


class TestProbe(_IsolatedHome):
    def test_probe_free_port_is_not_devos(self) -> None:
        # On Windows the firewall silently drops SYNs to closed loopback ports,
        # so "free" vs "hung occupant" is indistinguishable from the connect
        # error — probe only answers "is this DeveloperOS?"; the *bind* decides
        # whether the port is takeable (D-0030).
        from devos.commands.app_cmd import probe
        self.assertFalse(probe(_free_port()))

    def test_probe_detects_devos(self) -> None:
        from devos.commands.app_cmd import probe
        port = _start_devos_server(self)
        self.assertTrue(probe(port))

    def test_probe_rejects_other_http_server(self) -> None:
        from devos.commands.app_cmd import probe
        port = _start_other_server(self)
        self.assertFalse(probe(port))


class TestLauncher(_IsolatedHome):
    def test_reuses_running_instance_instead_of_starting_twice(self) -> None:
        from devos.commands import app_cmd
        port = _start_devos_server(self)
        opened: list[str] = []
        starts: list[int] = []
        orig_ui = app_cmd._open_ui
        app_cmd._open_ui = lambda url, **k: opened.append(url)
        from devos.api import server as api_server
        orig_create = api_server.create_server
        api_server.create_server = lambda *a, **k: starts.append(1)
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(["app", "--port", str(port)])
        finally:
            app_cmd._open_ui = orig_ui
            api_server.create_server = orig_create
        self.assertEqual(code, 0)
        self.assertEqual(opened, [f"http://127.0.0.1:{port}"])
        self.assertEqual(starts, [], "must not start a second server")
        self.assertIn("already running", buf.getvalue().lower())

    def test_port_conflict_gives_friendly_error(self) -> None:
        port = _start_other_server(self)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["app", "--port", str(port), "--no-browser"])
        self.assertEqual(code, 1)
        self.assertIn("--port", buf.getvalue(), "should suggest trying another port")

    def test_fresh_start_auto_inits_and_serves(self) -> None:
        from devos.api import server as api_server

        class StubServer:
            server_address = ("127.0.0.1", 8765)
            served = False

            def serve_forever(self):
                StubServer.served = True

            def server_close(self):
                pass

        orig_create = api_server.create_server
        api_server.create_server = lambda *a, **k: StubServer()
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(["app", "--no-browser", "--port", str(_free_port())])
        finally:
            api_server.create_server = orig_create
        self.assertEqual(code, 0)
        self.assertTrue(StubServer.served)
        self.assertTrue(Workspace.load().is_initialized(),
                        "launcher must auto-initialize a fresh home")


class TestAppWindow(unittest.TestCase):
    """Slice 16 (D-0033): standalone app-mode window via Edge/Chrome --app."""

    def test_find_app_browser_returns_existing_path_or_none(self) -> None:
        from devos.commands.app_cmd import _find_app_browser
        path = _find_app_browser()
        if path is not None:
            self.assertTrue(os.path.isfile(path), f"{path} should exist")

    def test_open_window_spawns_app_mode_process(self) -> None:
        from devos.commands import app_cmd
        calls: list[list[str]] = []
        orig_find, orig_popen = app_cmd._find_app_browser, app_cmd.subprocess.Popen
        app_cmd._find_app_browser = lambda: r"C:\fake\msedge.exe"
        app_cmd.subprocess.Popen = lambda argv, **k: calls.append(argv)
        try:
            ok = app_cmd._open_window("http://127.0.0.1:9999")
        finally:
            app_cmd._find_app_browser = orig_find
            app_cmd.subprocess.Popen = orig_popen
        self.assertTrue(ok)
        self.assertEqual(calls[0][0], r"C:\fake\msedge.exe")
        self.assertIn("--app=http://127.0.0.1:9999", calls[0])

    def test_open_ui_falls_back_to_default_browser(self) -> None:
        from devos.commands import app_cmd
        opened: list[str] = []
        orig_find, orig_open = app_cmd._find_app_browser, app_cmd.webbrowser.open
        app_cmd._find_app_browser = lambda: None
        app_cmd.webbrowser.open = lambda url: opened.append(url) or True
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                app_cmd._open_ui("http://127.0.0.1:9999")
        finally:
            app_cmd._find_app_browser = orig_find
            app_cmd.webbrowser.open = orig_open
        self.assertEqual(opened, ["http://127.0.0.1:9999"])

    def test_open_ui_plain_forces_browser_tab(self) -> None:
        from devos.commands import app_cmd
        opened: list[str] = []
        windows: list[str] = []
        orig_win, orig_open = app_cmd._open_window, app_cmd.webbrowser.open
        app_cmd._open_window = lambda url: windows.append(url) or True
        app_cmd.webbrowser.open = lambda url: opened.append(url) or True
        try:
            app_cmd._open_ui("http://127.0.0.1:9999", plain=True)
        finally:
            app_cmd._open_window = orig_win
            app_cmd.webbrowser.open = orig_open
        self.assertEqual(opened, ["http://127.0.0.1:9999"])
        self.assertEqual(windows, [], "--browser must bypass the app window")

    def test_app_has_browser_flag(self) -> None:
        import argparse
        from devos.commands.app_cmd import AppCommand
        parser = argparse.ArgumentParser()
        AppCommand().configure(parser)
        args = parser.parse_args(["--browser"])
        self.assertTrue(args.browser)


if __name__ == "__main__":
    unittest.main()
