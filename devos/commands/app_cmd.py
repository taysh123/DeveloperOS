"""`devos app` — launch DeveloperOS like a desktop app (D-0029 ladder step B).

Lifecycle (D-0030): probe -> reuse-or-start -> ready-wait -> open -> serve
(blocking) -> Ctrl+C graceful stop. Single instance per port is guaranteed by a
**read-only** probe of GET /api/session: if a DeveloperOS dashboard already
answers we open the browser at it instead of starting a second server; if
something else owns the port we print a friendly suggestion instead of crashing.
Loopback-only and offline like everything else — no new API surface.
"""
from __future__ import annotations

import argparse
import http.client
import json
import socket
import threading
import time
import urllib.error
import urllib.request
import webbrowser

from devos.commands.base import Command, register
from devos.core.workspace import Workspace

PROBE_TIMEOUT = 1.0
READY_ATTEMPTS = 25   # x READY_DELAY = ~5 s worst case before opening anyway
READY_DELAY = 0.2


def probe(port: int, *, host: str = "127.0.0.1") -> bool:
    """True iff a DeveloperOS dashboard answers on the port.

    Identified by GET /api/session answering 200 with a JSON object carrying a
    "token" key — cheap, unambiguous, and read-only. Anything else (no answer,
    other server, junk) is False; whether the port is *takeable* is decided by
    the bind itself, not by exception archaeology — on Windows the firewall
    silently drops SYNs to closed loopback ports, so "refused" vs "free" can't
    be told apart from the connect error.
    """
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/session",
                                    timeout=PROBE_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return isinstance(data, dict) and "token" in data
    except (urllib.error.URLError, http.client.HTTPException,
            TimeoutError, ValueError, OSError):
        return False


def _port_takeable(port: int, *, host: str = "127.0.0.1") -> bool:
    """True iff we could bind the port exclusively right now.

    Deliberately a *plain* socket without SO_REUSEADDR: stdlib HTTPServer sets
    allow_reuse_address, and on Windows SO_REUSEADDR lets a second bind to an
    occupied port succeed silently — so create_server() raising OSError cannot
    be relied on as the "occupied" signal there.
    """
    s = socket.socket()
    try:
        s.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _open_when_ready(url: str) -> None:
    """Wait for the dashboard to answer, then open the default browser."""
    for _ in range(READY_ATTEMPTS):
        try:
            urllib.request.urlopen(url + "/api/session", timeout=1)
            break
        except Exception:
            time.sleep(READY_DELAY)
    webbrowser.open(url)


@register
class AppCommand(Command):
    name = "app"
    help = "Launch DeveloperOS: start the dashboard (if needed) and open it in your browser."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--port", type=int, default=8765, help="Port (default 8765).")
        parser.add_argument("--no-browser", action="store_true",
                            help="Don't open a browser window (for scripts/tests).")

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if not ws.is_initialized():
            ws.initialize().close()
            print("First run — created your local DeveloperOS data folder.")

        url = f"http://127.0.0.1:{args.port}"
        if probe(args.port):
            print(f"DeveloperOS is already running at {url} — opening it.")
            if not args.no_browser:
                webbrowser.open(url)
            return 0

        if not _port_takeable(args.port):
            print(f"Port {args.port} is being used by another program.")
            print(f"Try a different one, e.g.:  devos app --port {args.port + 5}")
            return 1
        from devos.api import server  # local import: only needed when serving
        try:
            srv = server.create_server("127.0.0.1", args.port)
        except OSError:
            # Lost the (tiny) race between the check above and the real bind.
            print(f"Port {args.port} is being used by another program.")
            print(f"Try a different one, e.g.:  devos app --port {args.port + 5}")
            return 1
        host, port = srv.server_address[0], srv.server_address[1]
        url = f"http://{host}:{port}"
        print(f"DeveloperOS is ready at {url}")
        if not args.no_browser:
            print("Opening your browser…")
            threading.Thread(target=_open_when_ready, args=(url,), daemon=True).start()
        print("Keep this window open while you use DeveloperOS; press Ctrl+C to stop.")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped.")
        finally:
            srv.server_close()
        return 0
