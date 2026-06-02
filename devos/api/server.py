"""Thin stdlib http.server wrapper around the `app.route` table.

Loopback-only by default (security: see docs/SECURITY.md sec. 8). Each request opens
its own Workspace/connection (sqlite connections are not shared across threads).

GET endpoints are read-only. POST endpoints perform guarded DB writes (tasks/notes) and
are protected at this HTTP boundary by: a per-server CSRF token (required in the
``X-DevOS-Token`` header, delivered same-origin via ``GET /api/session``), an Origin
allowlist (loopback only), a JSON content-type requirement, and a request-size cap.
No CORS headers are ever emitted, so a cross-origin page can neither read API responses
nor obtain the token.
"""
from __future__ import annotations

import hmac
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from devos.api import app
from devos.core.workspace import Workspace

MAX_BODY_BYTES = 64 * 1024  # request-size cap for write endpoints


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # -- helpers ----------------------------------------------------------
    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_resp(self, resp) -> None:
        self._send(resp.status, resp.content_type, resp.body)

    def _send_json(self, obj, status: int = 200) -> None:
        self._send(status, "application/json; charset=utf-8",
                   json.dumps(obj).encode("utf-8"))

    def _reject(self, obj, status: int) -> None:
        """Send an error response and close the connection (body not drained)."""
        self.close_connection = True
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _allowed_origins(self) -> set[str]:
        port = self.server.server_address[1]
        return {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

    # -- verbs ------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        parsed = urlparse(self.path)
        if parsed.path == "/api/session":
            self._send_json({"token": self.server.csrf_token})
            return
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        ws = self.server.ws_factory()
        self._send_resp(app.route(ws, parsed.path, query, method="GET"))

    def do_POST(self) -> None:  # noqa: N802 (stdlib naming)
        # 1) Request-size cap (checked before reading; close on reject so we never
        #    have to drain an oversized/garbled body).
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._reject({"error": "invalid Content-Length"}, 400)
            return
        if length < 0 or length > MAX_BODY_BYTES:
            self._reject({"error": "request too large"}, 413)
            return
        # 2) Read the (bounded) body up front. Doing this BEFORE the auth checks keeps
        #    the HTTP/1.1 connection consistent on early rejection — otherwise responding
        #    without consuming the body can desync keep-alive and surface as a client-side
        #    connection reset instead of the intended status code.
        raw = self.rfile.read(length) if length else b""
        # 3) Origin allowlist (defense-in-depth against cross-site requests).
        origin = self.headers.get("Origin")
        if origin is not None and origin not in self._allowed_origins():
            self._send_json({"error": "forbidden origin"}, 403)
            return
        # 4) CSRF token (constant-time compare).
        token = self.headers.get("X-DevOS-Token", "")
        if not hmac.compare_digest(token, self.server.csrf_token):
            self._send_json({"error": "missing or invalid token"}, 403)
            return
        # 5) JSON content-type required (forces a preflight for cross-origin writes).
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            self._send_json({"error": "content-type must be application/json"}, 415)
            return
        # 6) Parse JSON body.
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except (ValueError, UnicodeDecodeError):
            self._send_json({"error": "invalid JSON body"}, 400)
            return
        if not isinstance(body, dict):
            self._send_json({"error": "JSON body must be an object"}, 400)
            return

        parsed = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        ws = self.server.ws_factory()
        self._send_resp(app.route(ws, parsed.path, query, method="POST", body=body))

    def log_message(self, *args) -> None:  # keep the console quiet
        pass


def create_server(host: str = "127.0.0.1", port: int = 8765,
                  ws_factory=Workspace.load) -> ThreadingHTTPServer:
    """Create (but do not start) a loopback dashboard server."""
    server = ThreadingHTTPServer((host, port), _Handler)
    server.ws_factory = ws_factory
    server.csrf_token = secrets.token_urlsafe(32)
    return server


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Create and run the server until interrupted (blocking)."""
    server = create_server(host, port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
