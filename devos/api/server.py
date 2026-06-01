"""Thin stdlib http.server wrapper around the read-only `app.route` table.

Loopback-only by default (security: see docs/SECURITY.md sec. 8). Each request opens
its own Workspace/connection (sqlite connections are not shared across threads).
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from devos.api import app
from devos.core.workspace import Workspace


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        parsed = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        ws = self.server.ws_factory()
        resp = app.route(ws, parsed.path, query)
        self.send_response(resp.status)
        self.send_header("Content-Type", resp.content_type)
        self.send_header("Content-Length", str(len(resp.body)))
        self.end_headers()
        self.wfile.write(resp.body)

    def log_message(self, *args) -> None:  # keep the console quiet
        pass


def create_server(host: str = "127.0.0.1", port: int = 8765,
                  ws_factory=Workspace.load) -> ThreadingHTTPServer:
    """Create (but do not start) a loopback dashboard server."""
    server = ThreadingHTTPServer((host, port), _Handler)
    server.ws_factory = ws_factory
    return server


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Create and run the server until interrupted (blocking)."""
    server = create_server(host, port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
